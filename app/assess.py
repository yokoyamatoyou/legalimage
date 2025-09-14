
import json
import yaml
from typing import Dict, List, Any

def load_rules_from_yaml(yaml_path: str = "app/rules.yml") -> List[Dict[str, Any]]:
    """
    YAMLファイルからルールパックを読み込む。
    
    Args:
        yaml_path: YAMLファイルのパス
        
    Returns:
        List[Dict]: ルールのリスト
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            return data.get('rules', [])
    except Exception as e:
        print(f"ルールファイルの読み込みに失敗しました: {e}")
        return []

def filter_rules_by_scene(rules: List[Dict[str, Any]], scene_tags: List[str], selected_rule_packs: List[str]) -> List[Dict[str, Any]]:
    """
    シーンタグと選択されたルールパックに基づいてルールをフィルタリングする。
    
    Args:
        rules: 全ルールのリスト
        scene_tags: シーン分類で得られたタグ
        selected_rule_packs: ユーザーが選択したルールパック
        
    Returns:
        List[Dict]: フィルタリングされたルールのリスト
    """
    filtered_rules = []
    
    for rule in rules:
        # ルールパックのフィルタリング
        rule_domain = rule.get('domain', '')
        if any(pack in rule_domain for pack in selected_rule_packs):
            filtered_rules.append(rule)
        # シーンタグとの関連性チェック（将来的に拡張可能）
        elif scene_tags and any(tag in rule.get('detection_cues', []) for tag in scene_tags):
            filtered_rules.append(rule)
    
    return filtered_rules

def process_ai_response(json_string: str, scene_tags: List[str] = None, selected_rule_packs: List[str] = None):
    """
    AIからの統合JSON応答を解析し、リスクスコアの計算とソートを行う。
    GPT-4.1-miniのマルチモーダル性能により、シーン分類とリスク評価が統合されている。

    Args:
        json_string: AI(models.py)から返された統合JSON形式の文字列
        scene_tags: 後方互換性のためのパラメータ（統合結果から自動取得）
        selected_rule_packs: 後方互換性のためのパラメータ（統合結果から自動取得）

    Returns:
        dict: 処理済みのデータ。findingsにはrisk_scoreが追加され、降順でソートされている。
              パースに失敗した場合は、エラー情報を含むdictを返す。
    """
    try:
        # 1. JSON文字列をPythonオブジェクトにパース
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        print(f"JSONのパースに失敗しました: {e}")
        return {"error": "AIの応答が有効なJSON形式ではありません。", "raw_response": json_string}

    if data.get("error"):
        return data # APIエラーが既に含まれている場合はそのまま返す

    # 2. 統合結果からシーン分析を抽出
    scene_analysis = data.get("scene_analysis", {})
    if scene_analysis:
        data["scene_tags"] = scene_analysis.get("scene_tags", [])
        data["risk_context"] = scene_analysis.get("risk_context", "")
        data["confidence"] = scene_analysis.get("confidence", 0.0)
    else:
        # 後方互換性のため
        data["scene_tags"] = scene_tags or []
        data["risk_context"] = ""
        data["confidence"] = 0.0

    # 3. ルールパックの読み込みとフィルタリング
    all_rules = load_rules_from_yaml()
    if selected_rule_packs or data["scene_tags"]:
        filtered_rules = filter_rules_by_scene(all_rules, data["scene_tags"], selected_rule_packs or [])
        data["applied_rules"] = [rule["rule_id"] for rule in filtered_rules]
    else:
        data["applied_rules"] = []

    # 4. リスクスコアの計算と追加
    findings = data.get("findings", [])
    for item in findings:
        components = item.get("risk_score_components", {})
        severity = components.get("severity", 0)
        likelihood = components.get("likelihood", 0)
        
        # AGENT.mdで定義された計算式
        risk_score = int(severity) * int(likelihood) * 10
        item["risk_score"] = risk_score

    # 5. リスクスコアで指摘事項を降順にソート
    sorted_findings = sorted(findings, key=lambda x: x.get("risk_score", 0), reverse=True)
    data["findings"] = sorted_findings
    
    return data

# --- 動作確認用のサンプルコード ---
if __name__ == '__main__':
    print("assess.py の動作確認...")
    
    # models.pyからの成功応答を模したダミーデータ
    mock_json_response = '''
    {
      "findings": [
        {
          "rule_id": "労安-墜落-001",
          "domain": "労働安全衛生",
          "judgment": "不明",
          "observation_reason": "ハーネスは視認できるが、接続点が不明瞭。",
          "standard_reason": "労働安全衛生規則 第518条（作業床の設置等）",
          "risk_score_components": {
            "severity": 3,
            "likelihood": 2
          },
          "additional_question": "作業床の高さ、親綱や安全ブロックの設置状況について教えてください。"
        },
        {
          "rule_id": "情報-離席-001",
          "domain": "情報セキュリティ",
          "judgment": "不適合",
          "observation_reason": "PCがロックされていない状態で作業者が離席している。",
          "standard_reason": "ISMS（情報セキュリティマネジメントシステム）の物理的管理策",
          "risk_score_components": {
            "severity": 2,
            "likelihood": 3
          },
          "additional_question": null
        }
      ],
      "suggestions": []
    }
    '''
    
    processed_data = process_ai_response(mock_json_response)
    
    if "error" in processed_data:
        print(f"エラーが発生しました: {processed_data['error']}")
    else:
        print("JSONの処理に成功しました。")
        print("--- リスクスコア順（降順） --- ")
        for finding in processed_data.get("findings", []):
            print(f"- ID: {finding['rule_id']}, Score: {finding['risk_score']}")
        # 1番目のスコアが90 (2*3*10) ではなく 60 (3*2*10) であればソート成功
        assert processed_data["findings"][0]["risk_score"] == 90
        assert processed_data["findings"][1]["risk_score"] == 60
        print("\nソートの検証OK")

    # エラーケースのテスト
    mock_error_json = '{"error": "APIキーが無効です"}'
    processed_error = process_ai_response(mock_error_json)
    print(f"\nエラーJSONの処理テスト: {processed_error}")
    assert "error" in processed_error

    mock_invalid_json = '{"key": "value' # 途中で切れたJSON
    processed_invalid = process_ai_response(mock_invalid_json)
    print(f"\n不正JSONの処理テスト: {processed_invalid}")
    assert "error" in processed_invalid
