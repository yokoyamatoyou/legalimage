"""
2段階推論による高精度分析
1段階目: 画像認識とシーン分類
2段階目: シーン情報を基にした詳細なリスク分析
"""

import json
import openai
from typing import Dict, List, Any

# 1段階目: 画像認識とシーン分類用のツールスキーマ
SCENE_ANALYSIS_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "analyze_scene",
        "description": "画像から作業現場の種類と基本的なリスク要因を分析する。",
        "parameters": {
            "type": "object",
            "properties": {
                "scene_tags": {
                    "type": "array",
                    "description": "検出された作業現場のタグリスト",
                    "items": {
                        "type": "string",
                        "enum": [
                            "建設現場", "高所作業", "配線作業", "電気工事", "機械作業",
                            "厨房", "調理作業", "食品加工", "清掃作業",
                            "オフィス", "PC作業", "書類作業", "会議",
                            "倉庫", "物流作業", "荷物運搬",
                            "工場", "製造作業", "組立作業", "検査作業",
                            "医療", "実験室", "研究作業",
                            "その他"
                        ]
                    }
                },
                "visual_elements": {
                    "type": "array",
                    "description": "画像から検出された視覚的要素",
                    "items": {
                        "type": "string"
                    }
                },
                "potential_risks": {
                    "type": "array",
                    "description": "画像から読み取れる潜在的なリスク要因",
                    "items": {
                        "type": "string"
                    }
                },
                "confidence": {
                    "type": "number",
                    "description": "分析の信頼度（0.0-1.0）",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["scene_tags", "visual_elements", "potential_risks", "confidence"]
        }
    }
}

# 2段階目: 詳細なリスク分析用のツールスキーマ
DETAILED_RISK_ANALYSIS_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "analyze_detailed_risks",
        "description": "シーン分析結果を基に、詳細な法的リスク分析を実行する。",
        "parameters": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "description": "必須(mandatory)の指摘事項リスト",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule_id": {"type": "string"},
                            "domain": {"type": "string"},
                            "judgment": {"type": "string", "enum": ["適合", "不適合", "不明"]},
                            "observation_reason": {"type": "string"},
                            "standard_reason": {"type": "string"},
                            "risk_score_components": {
                                "type": "object",
                                "properties": {
                                    "severity": {"type": "integer"},
                                    "likelihood": {"type": "integer"}
                                },
                                "required": ["severity", "likelihood"]
                            },
                            "additional_question": {"type": "string"}
                        },
                        "required": ["rule_id", "domain", "judgment", "observation_reason", "standard_reason", "risk_score_components"]
                    }
                },
                "suggestions": {
                    "type": "array",
                    "description": "ベストプラクティスなどの提案事項リスト",
                    "items": {
                        "type": "object",
                        "properties": {
                            "domain": {"type": "string"},
                            "suggestion": {"type": "string"},
                            "evidence": {"type": "string"}
                        },
                        "required": ["domain", "suggestion", "evidence"]
                    }
                }
            },
            "required": ["findings", "suggestions"]
        }
    }
}

def stage1_scene_analysis(client: openai.OpenAI, user_prompt: str, base64_images: List[str], model: str) -> Dict[str, Any]:
    """
    1段階目: 画像認識とシーン分類
    """
    SYSTEM_PROMPT = """あなたは画像分析の専門家です。画像を詳細に観察し、作業現場の種類と基本的なリスク要因を特定してください。

以下の観点で分析してください：
1. 作業現場の種類（建設現場、厨房、オフィスなど）
2. 画像に写っている具体的な要素（人物、設備、環境など）
3. 潜在的なリスク要因（安全設備の有無、作業環境の状態など）

analyze_scene関数を呼び出して結果を構造化してください。"""
    
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "text", "text": user_prompt}] + \
                [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}} for b64_img in base64_images]}
        ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[SCENE_ANALYSIS_TOOL_SCHEMA],
            tool_choice={"type": "function", "function": {"name": "analyze_scene"}},
            max_tokens=2000,
        )
        
        result_json = response.choices[0].message.tool_calls[0].function.arguments
        return json.loads(result_json)

    except Exception as e:
        return {"error": f"1段階目分析でエラーが発生しました: {e}"}

def stage2_risk_analysis(client: openai.OpenAI, user_prompt: str, scene_analysis: Dict[str, Any], model: str) -> Dict[str, Any]:
    """
    2段階目: シーン分析結果を基にした詳細なリスク分析
    """
    # シーン分析結果をプロンプトに組み込む
    scene_context = f"""
シーン分析結果:
- 作業現場: {', '.join(scene_analysis.get('scene_tags', []))}
- 視覚的要素: {', '.join(scene_analysis.get('visual_elements', []))}
- 潜在リスク: {', '.join(scene_analysis.get('potential_risks', []))}
- 信頼度: {scene_analysis.get('confidence', 0.0):.1%}
"""
    
    SYSTEM_PROMPT = f"""あなたは労働安全、建築、食品衛生、情報セキュリティの法規制とベストプラクティスに精通した監査エージェントです。

{scene_context}

上記のシーン分析結果を基に、以下の観点で詳細な法的リスク分析を実行してください：
1. 関連する法令・規格への照合
2. 具体的な違反事項の特定
3. リスクの重大度と発生可能性の評価
4. 改善提案の生成

analyze_detailed_risks関数を呼び出して結果を構造化してください。"""
    
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[DETAILED_RISK_ANALYSIS_TOOL_SCHEMA],
            tool_choice={"type": "function", "function": {"name": "analyze_detailed_risks"}},
            max_tokens=4000,
        )
        
        result_json = response.choices[0].message.tool_calls[0].function.arguments
        detailed_analysis = json.loads(result_json)
        
        # シーン分析結果と詳細分析結果を統合
        return {
            "scene_analysis": scene_analysis,
            "findings": detailed_analysis.get("findings", []),
            "suggestions": detailed_analysis.get("suggestions", [])
        }

    except Exception as e:
        return {"error": f"2段階目分析でエラーが発生しました: {e}"}

def two_stage_analysis(client: openai.OpenAI, user_prompt: str, base64_images: List[str], model: str) -> Dict[str, Any]:
    """
    2段階推論による統合分析
    """
    # 1段階目: 画像認識とシーン分類
    scene_analysis = stage1_scene_analysis(client, user_prompt, base64_images, model)
    
    if "error" in scene_analysis:
        return scene_analysis
    
    # 2段階目: 詳細なリスク分析
    detailed_analysis = stage2_risk_analysis(client, user_prompt, scene_analysis, model)
    
    if "error" in detailed_analysis:
        return detailed_analysis
    
    return detailed_analysis

# --- 動作確認用のサンプルコード ---
if __name__ == '__main__':
    print("2段階推論の動作確認...")
    
    # 1段階目のテストデータ
    mock_scene_analysis = {
        "scene_tags": ["建設現場", "高所作業"],
        "visual_elements": ["作業員", "ハーネス", "足場", "工具"],
        "potential_risks": ["ハーネスの接続状況不明", "手すりの不備"],
        "confidence": 0.85
    }
    
    print(f"1段階目結果: {mock_scene_analysis}")
    
    # 2段階目のテスト（実際のAPI呼び出しなし）
    print("2段階目は実際のAPI呼び出しが必要です。")



