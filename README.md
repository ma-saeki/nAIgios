# nAIgios

Claude Code の UserPromptSubmit hook として動作するプロンプト品質モニタリングシステム。

オープンクエスチョン（機械が実行困難な曖昧なリクエスト）をリアルタイムで検知し、`/prompt-perfect` スキルの自動起動を Claude に指示します。

## インストール

```bash
# 1. スキルファイルを配置
cp -r skills/naigios-eval ~/.claude/skills/
cp -r skills/naigios ~/.claude/skills/
cp -r skills/prompt-perfect ~/.claude/skills/

# 2. hook に実行権限を付与
chmod +x ~/.claude/skills/naigios-eval/hook.py

# 3. ~/.claude/settings.json に hook を登録
```

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/skills/naigios-eval/hook.py"
          }
        ]
      }
    ]
  }
}
```

```bash
# 4. Claude Code を再起動後、ON にする
/naigios on
```

## 使い方

| コマンド | 動作 |
|---|---|
| `/naigios on` | 有効化 |
| `/naigios off` | 無効化 |
| `/naigios` | 状態確認 |

## 評価スコアリング

5軸（明瞭性・完全性・無矛盾性・直接性・可操作性）で 0〜100 点満点。**70 点未満** で OPEN 判定 → prompt-perfect が自動起動。

## 前提条件

- macOS + Claude Code VSCode 拡張
- Python 3.9 以上（stdlib のみ使用）
