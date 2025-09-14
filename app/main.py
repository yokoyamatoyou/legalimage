import streamlit as st
import pandas as pd
try:
    # プロジェクトルートがsys.pathにある場合
    from app import models, utils, assess  # 統合されたモジュールをインポート
except ModuleNotFoundError:
    # Streamlitがスクリプトディレクトリ（app/）をカレントにする場合のフォールバック
    import os, sys
    sys.path.append(os.path.dirname(__file__))
    import models, utils, assess

# --- ページ設定 ---
st.set_page_config(page_title="労働環境ガバナンスチェック", page_icon="🛡️", layout="wide")

# --- 初期化処理 ---
if 'openai_client' not in st.session_state:
    try:
        st.session_state.openai_client = models.get_openai_client()
        st.session_state.status_message = "<div style='text-align: right; color: green;'>✅ OpenAI接続完了</div>"
    except (ValueError, ConnectionError) as e:
        st.session_state.openai_client = None
        st.session_state.status_message = f"<div style='text-align: right; color: red;'>❌ {e}</div>"

# --- ウィジェット用デフォルト（作成前に一度だけ設定） ---
if 'gpt5_reasoning_effort' not in st.session_state:
    st.session_state['gpt5_reasoning_effort'] = 'medium'
if 'gpt5_verbosity' not in st.session_state:
    st.session_state['gpt5_verbosity'] = 'medium'
if 'gpt4_temperature' not in st.session_state:
    st.session_state['gpt4_temperature'] = 0.0
if 'gpt4_max_tokens' not in st.session_state:
    st.session_state['gpt4_max_tokens'] = 4000

# --- ヘッダー ---
with st.container():
    st.title("労働環境ガバナンスチェック")
    if 'status_message' in st.session_state:
        st.markdown(st.session_state.status_message, unsafe_allow_html=True)
    # UIの各要素をセッションステートで管理
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        st.selectbox("モデル", ("gpt-4.1-mini-2025-04-14", "gpt-4.1", "gpt-5-mini"), key="model_selection")
    with col2:
        st.multiselect("ルールパック", ["労安", "建築/電気", "食品", "情報保護", "ISO"], default=["労安"], key="rule_pack_selection")
    with col3:
        if st.session_state.model_selection == "gpt-5-mini":
            reasoning = st.session_state.get("gpt5_reasoning_effort", "medium")
            verbosity = st.session_state.get("gpt5_verbosity", "medium")
            st.markdown(f"""<div style='font-size: 0.9em; color: grey; text-align: right;'>
                reasoning_effort={reasoning} | verbosity={verbosity}<br>
                推論の深さとアウトプット量を調整可能
            </div>""", unsafe_allow_html=True)
        else:
            temperature = st.session_state.get("gpt4_temperature", 0.0)
            max_tokens = st.session_state.get("gpt4_max_tokens", 4000)
            st.markdown(f"""<div style='font-size: 0.9em; color: grey; text-align: right;'>
                temperature={temperature} | max_tokens={max_tokens}<br>
                温度設定とトークン数を調整可能
            </div>""", unsafe_allow_html=True)

# モデル別パラメータ設定UI
with st.expander("🔧 モデルパラメータ設定", expanded=False):
    selected_model = st.session_state.model_selection
    
    if selected_model == "gpt-5-mini":
        st.markdown("**GPT-5 mini パラメータ**")
        col1, col2 = st.columns(2)
        
        with col1:
            reasoning_effort = st.selectbox(
                "推論の深さ (reasoning_effort)",
                ["minimal", "low", "medium", "high"],
                index=2,  # mediumをデフォルト
                help="minimal: 高速・低コスト、high: 高精度・高コスト",
                key="gpt5_reasoning_effort"
            )
            
            # 推論の深さの説明
            if reasoning_effort == "minimal":
                st.info("⚡ 高速処理・低コスト（基本的な分析）")
            elif reasoning_effort == "low":
                st.info("🚀 高速処理・中コスト（標準的な分析）")
            elif reasoning_effort == "medium":
                st.info("⚖️ バランス型・中コスト（推奨設定）")
            else:  # high
                st.info("🎯 高精度・高コスト（複雑な分析）")
        
        with col2:
            verbosity = st.selectbox(
                "アウトプット量 (verbosity)",
                ["low", "medium", "high"],
                index=1,  # mediumをデフォルト
                help="low: 簡潔、high: 詳細",
                key="gpt5_verbosity"
            )
            
            # アウトプット量の説明
            if verbosity == "low":
                st.info("📝 簡潔な要約（要点のみ）")
            elif verbosity == "medium":
                st.info("📋 標準的な詳細（推奨設定）")
            else:  # high
                st.info("📚 詳細な分析（包括的）")
    
    elif selected_model in ["gpt-4.1-mini-2025-04-14", "gpt-4.1"]:
        st.markdown("**GPT-4.1系 パラメータ**")
        col1, col2 = st.columns(2)
        
        with col1:
            temperature = st.slider(
                "温度設定 (temperature)",
                min_value=0.0,
                max_value=2.0,
                value=0.0 if selected_model == "gpt-4.1-mini-2025-04-14" else 0.7,
                step=0.1,
                help="0.0: 確定的・一貫性重視、2.0: 創造的・多様性重視",
                key="gpt4_temperature"
            )
            
            # 温度設定の説明
            if temperature <= 0.3:
                st.info("🎯 確定的・一貫性重視（義務判定に適している）")
            elif temperature <= 0.7:
                st.info("⚖️ バランス型（標準的な分析）")
            else:
                st.info("💡 創造的・多様性重視（提案生成に適している）")
        
        with col2:
            max_tokens = st.slider(
                "最大トークン数 (max_tokens)",
                min_value=1000,
                max_value=8000,
                value=4000,
                step=500,
                help="応答の最大長を制御",
                key="gpt4_max_tokens"
            )
            
            st.info(f"📊 最大 {max_tokens} トークンまで生成")
    
    # パラメータの保存（ウィジェットキーはウィジェットに委ねるため、明示代入しない）
    
    # 現在の設定を表示
    st.markdown("---")
    st.markdown("**現在の設定**")
    if selected_model == "gpt-5-mini":
        st.code(f"モデル: {selected_model}\n推論の深さ: {reasoning_effort}\nアウトプット量: {verbosity}")
    else:
        st.code(f"モデル: {selected_model}\n温度: {temperature}\n最大トークン数: {max_tokens}")

st.divider()

# --- メインコンテンツ ---
left_column, right_column = st.columns(2)
with left_column:
    st.subheader("1. 画像アップロード")
    uploaded_files = st.file_uploader("監査対象の画像をドラッグ＆ドロップ", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    
    # セキュリティオプション
    col1, col2 = st.columns(2)
    with col1:
        remove_exif = st.checkbox("EXIF除去", value=True, help="画像から位置情報などのメタデータを除去します")
    with col2:
        blur_pii = st.checkbox("PIIぼかし", value=False, help="個人を特定できる情報をぼかします（開発中）")
    
    if uploaded_files:
        # 画像の検証とプレビュー
        valid_files = []
        for file in uploaded_files:
            validation = utils.validate_image_file(file)
            if validation['valid']:
                valid_files.append(file)
            else:
                st.error(f"❌ {file.name}: {validation['error']}")
        
        if valid_files:
            cols = st.columns(4)
            for i, file in enumerate(valid_files):
                with cols[i % 4]:
                    st.image(file, caption=file.name, use_container_width=True)
                    # メタデータ表示
                    metadata = utils.validate_image_file(file)['metadata']
                    st.caption(f"📏 {metadata['dimensions']} | 📦 {metadata['size']/1024:.0f}KB")

with right_column:
    st.subheader("2. 状況説明")
    st.caption("例: 『電気工事の高所作業で分電盤交換。作業床2.5m、親綱あり。該当規格: 労安/電気設備/ISMS(物理)』")
    st.text_area("作業内容と該当/準拠規格をできるだけ具体的に記載してください。", height=160, key="description_input")
    st.subheader("3. 解析実行")
    if st.button("解析開始 ▶", use_container_width=True, disabled=(st.session_state.openai_client is None)):
        if 'processed_data' in st.session_state: del st.session_state['processed_data']
        if not uploaded_files or not st.session_state.description_input.strip():
            st.warning("画像と状況説明の両方を入力してください。")
        else:
            with st.spinner("AIが解析中です..."):
                # 1. 画像の安全な処理
                image_results = []
                for file in uploaded_files:
                    result = utils.image_to_base64(file, remove_exif_data=remove_exif, blur_pii_data=blur_pii)
                    if result['success']:
                        image_results.append(result)
                    else:
                        st.error(f"❌ {file.name}: {result['error']}")
                
                if not image_results:
                    st.error("有効な画像がありません。")
                    st.stop()
                
                base64_images = [result['base64'] for result in image_results]
                
                # 2. 統合分析（シーン分類 + リスク評価）
                with st.spinner("作業現場を分析し、リスクを評価中..."):
                    # モデル別のカスタムパラメータを準備
                    custom_params = None
                    if st.session_state.model_selection == "gpt-5-mini":
                        custom_params = {
                            "reasoning_effort": st.session_state.get("gpt5_reasoning_effort", "medium"),
                            "verbosity": st.session_state.get("gpt5_verbosity", "medium")
                        }
                    elif st.session_state.model_selection in ["gpt-4.1-mini-2025-04-14", "gpt-4.1"]:
                        custom_params = {
                            "temperature": st.session_state.get("gpt4_temperature", 0.0),
                            "max_tokens": st.session_state.get("gpt4_max_tokens", 4000)
                        }
                    
                    ai_response_json = models.call_vision_api(
                        st.session_state.openai_client, 
                        st.session_state.description_input, 
                        base64_images, 
                        st.session_state.model_selection,
                        custom_params
                    )
                    processed_data = assess.process_ai_response(ai_response_json)
                
                st.session_state.processed_data = processed_data
                if "error" in processed_data:
                    error_msg = processed_data['error']
                    st.error(f"解析中にエラーが発生しました: {error_msg}")
                    
                    # パラメータ関連のエラーの場合は詳細を表示
                    if "パラメータ" in error_msg or "APIリクエストエラー" in error_msg:
                        st.warning("💡 **解決方法**: モデルパラメータ設定を確認し、適切な値を選択してください。")
                        st.info("**推奨設定**: GPT-5 miniの場合はreasoning_effort=medium, verbosity=mediumを試してください。")
                else:
                    # シーン分析結果の表示
                    if 'scene_tags' in processed_data and processed_data['scene_tags']:
                        st.success(f"🔍 **検出された作業現場**: {', '.join(processed_data['scene_tags'])}")
                    if 'confidence' in processed_data:
                        st.info(f"📊 **分析信頼度**: {processed_data['confidence']:.1%}")
                    st.success("AIによる統合解析が完了しました。結果を以下に表示します。")
                    st.caption("※ 本結果は監査支援を目的とした自動解析です。法改正等により最新でない可能性があります。最終確認は利用者の責任でお願いします。")

st.divider()

# --- 結果表示タブ ---
st.subheader("4. 解析結果")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["① 義務(温度0)", "② 提案(温度0.7)", "③ 重要度ビュー", "④ Q&Aログ", "⑤ PDF"])

if 'processed_data' in st.session_state and "error" not in st.session_state.processed_data:
    data = st.session_state.processed_data
    
    # シーン推定結果の表示
    if 'scene_tags' in data and data['scene_tags']:
        st.info(f"🔍 **検出された作業現場**: {', '.join(data['scene_tags'])}")
    
    if 'applied_rules' in data and data['applied_rules']:
        st.info(f"📋 **適用されたルール**: {', '.join(data['applied_rules'])}")
    
    # --- 義務タブ --- 
    with tab1:
        st.header("義務（必須/準拠必須）事項の指摘")
        findings = data.get("findings", [])
        if not findings:
            st.success("義務違反に該当する指摘事項は見つかりませんでした。")
        for item in findings:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{item.get('domain', 'N/A')} / {item.get('rule_id', 'N/A')}**")
                with col2:
                     st.error(f"Risk Score: {item.get('risk_score', 0)}")
                st.markdown(f"**判定:** {item.get('judgment', 'N/A')}")
                st.markdown(f"**観察根拠:** {item.get('observation_reason', 'N/A')}")
                st.markdown(f"**規格根拠:** {item.get('standard_reason', 'N/A')}")
                if item.get('additional_question'):
                    st.info(f"**追加質問:** {item.get('additional_question', 'N/A')}")

    # --- 提案タブ --- 
    with tab2:
        st.header("提案（ベストプラクティス）事項")
        suggestions = data.get("suggestions", [])
        if not suggestions:
            st.info("提案事項は見つかりませんでした。")
        for item in suggestions:
            with st.container(border=True):
                st.markdown(f"**{item.get('domain', 'N/A')}**")
                st.markdown(f"**提案:** {item.get('suggestion', 'N/A')}")
                st.markdown(f"**根拠:** {item.get('evidence', 'N/A')}")

    # --- 重要度ビュータブ --- 
    with tab3:
        st.header("リスク重要度ビュー")
        if not findings:
            st.info("グラフ化する指摘事項がありません。")
        else:
            chart_data = pd.DataFrame(
                [{"指摘事項": f"{f.get('rule_id')}", "リスクスコア": f.get('risk_score')} for f in findings]
            ).set_index("指摘事項")
            st.bar_chart(chart_data)

    with tab4:
        st.header("AIとのQ&Aログ（不足情報の確認）")
        questions = [f for f in data.get("findings", []) if f.get("additional_question")]
        if not questions:
            st.info("現在、確認すべき追加質問はありません。")
        else:
            for q in questions:
                st.write(f"- {q.get('additional_question')}")

    with tab5:
        st.header("PDFレポートのエクスポート")
        st.info("この機能は現在開発中です。")
else:
    with tab1:
        st.info("解析を開始すると、ここに義務に関する指摘が表示されます。")
    with tab2:
        st.info("解析を開始すると、ここに提案事項が表示されます。")
    with tab3:
        st.info("解析を開始すると、ここにリスクのグラフが表示されます。")