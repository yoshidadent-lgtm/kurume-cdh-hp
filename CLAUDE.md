# プロジェクトメモ

## 目標
- 久留米歯科衛生専門学校（英語名：Kurume College of Dental Hygiene ※綴りはユーザー確認待ち）の公式サイトを、GitHub Pages で運用する静的サイトとして新規に作る。
- 本会（久留米歯科医師会）のサイト `yoshidadent-lgtm/kurumedental-hp` と同じ方式で作る（`data/` と `templates/` から `tools/build.py` で生成）。
- 新しい固有アドレス（独自ドメイン）を新規に取得し、GitHub 上で運用する。本会サイトとは独立（DNSも別管理）。
- 旧サイト `/kdhs/`（kurume-dental.or.jp 配下の別WordPress）は、新サイト公開まで今のまま残し、公開後に新アドレスへ 301 転送する（設定は学校の担当者）。

## 作業ルール
- 素材（画像・動画など）は基本的にすべてクラウド上で扱い、GitHub リポジトリに直接置く。動画は YouTube 等に置いて埋め込む。ローカルPCのSSD空きが少ない。
- `main` への push は、変更後の画面をユーザーに見せ、ユーザーが「mainにpushして」と言ってから行う。それまでは作業ブランチにのみ push する。
- ユーザーがプロンプトに書いた方針や前提は、このファイルに追記する。

## セキュリティ
- 会員向け・パスワード保護・個人情報（メールアドレス等）は、リポジトリに置かない。
- WordPressのエクスポートXMLは、GitHubにアップロードしない。非公開の投稿・パスワード・メールを取り除いた版だけを置く。
- 外部CDNに頼らず、必要な部品は自前で置く。

## 運用
- リポジトリは個人アカウント `yoshidadent-lgtm/kurume-cdh-hp`（Public）。完成後、Organization `kurume-dental-association` へ移す予定（移動後は Pages・Secrets・権限・セッション接続を再確認）。
- 現在の `index.html` は「HP改善・週次進捗管理」ツール（学校サイトとは無関係）。扱いは、ユーザーに確認中。
