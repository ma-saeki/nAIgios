---
invoke: user
description: nAIgios の ON/OFF を切り替える。引数なしで現在の状態を表示。"on" で有効化、"off" で無効化。
---

# nAIgios トグル

引数 `$args` に応じて以下を実行してください。

## on の場合

```bash
touch ~/.claude/.naigios_active
```

を実行し、「nAIgios: ON になりました。以降のリクエストは自動評価されます。」と伝えてください。

## off の場合

```bash
rm -f ~/.claude/.naigios_active
```

を実行し、「nAIgios: OFF になりました。」と伝えてください。

## 引数なし（状態確認）の場合

```bash
[ -f ~/.claude/.naigios_active ] && echo "ON" || echo "OFF"
```

を実行し、現在の状態を伝えてください。

---

$args
