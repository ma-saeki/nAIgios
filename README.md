# nAIgios

Claude Code の UserPromptSubmit hook として動作するプロンプト品質モニタリングシステム。

オープンクエスチョン（機械が実行困難な曖昧なリクエスト）をリアルタイムで検知し、`/prompt-perfect` スキルの自動起動を Claude に指示します。

## リポジトリ構成

このリポジトリのディレクトリ構造は `~/.claude/` に直接対応しています。

```
.claude/
├── skills/
│   ├── naigios-eval/      ← hook 本体・評価プロンプト
│   │   ├── hook.py
│   │   ├── eval_prompt.txt
│   │   └── SKILL.md
│   ├── naigios/           ← /naigios on|off トグルスキル
│   │   └── SKILL.md
│   └── prompt-perfect/    ← オープンクエスチョン改善スキル
│       └── SKILL.md
└── settings.json.example  ← hook 登録テンプレート
```

## インストール

```bash
git clone https://github.com/ma-saeki/nAIgios
cp -r nAIgios/.claude ~/
chmod +x ~/.claude/skills/naigios-eval/hook.py
```

`~/.claude/settings.json` に hook を追加します（既存の設定がある場合はマージしてください）：

```bash
cat ~/.claude/settings.json.example
# 内容を ~/.claude/settings.json の "hooks" セクションに追記
```

Claude Code を再起動後、有効化します：

```
/naigios on
```

## 使い方

| コマンド | 動作 |
|---|---|
| `/naigios on` | 有効化 |
| `/naigios off` | 無効化 |
| `/naigios` | 状態確認 |

## 評価スコアリング

5軸（明瞭性・完全性・無矛盾性・直接性・可操作性）で 0〜100 点満点。**70 点未満** で OPEN 判定 → `claude-haiku-4-5-20251001` が評価し、prompt-perfect が自動起動。

直前のアシスタントの発言もコンテキストとして加味するため、確認質問への短い返答は false positive になりません。

## 前提条件

- macOS + Claude Code VSCode 拡張
- Python 3.9 以上（stdlib のみ使用）
