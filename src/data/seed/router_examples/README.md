# Router Examples - JSONL Format

## 📝 How to Edit

### Format

Each line is a JSON object with:

```jsonl
{"example": "query text", "intent": "search|chat", "language": "pt|en|es", "category": "..."}
```

### Fields

| Field | Required | Values | Description |
|-------|----------|--------|-------------|
| `example` | ✅ | string | The example query |
| `intent` | ✅ | `search` or `chat` | Which intent this example should route to |
| `language` | ✅ | `pt`, `en`, or `es` | Language code |
| `category` | ❌ | any string | Optional category for organization |

### Categories (optional, for organization)

**Chat categories:**
- `question` - How/what/why questions
- `help` - Help requests
- `escalation` - Want to talk to human
- `greeting` - Hi, hello, etc
- `issue` - Problems/complaints
- `info` - Information requests

**Search categories:**
- `banking` - Banking services (pix, boleto, etc)
- `shopping` - Product searches (buy iphone, etc)

---

## ✏️ Examples

### Add a new PT chat example

Open `pt_chat.jsonl` and add:

```jsonl
{"example": "quero falar com supervisor", "intent": "chat", "language": "pt", "category": "escalation"}
```

### Add a new EN search example

Open `en_search.jsonl` and add:

```jsonl
{"example": "cryptocurrency", "intent": "search", "language": "en", "category": "banking"}
```

---

## 🔄 How to Reload

After editing, restart the server:

```bash
./run.sh
```

Or reload the router (if you implement hot reload).

---

## 📊 Current Stats

Run this to see counts:

```bash
python -c "from src.data.seed import load_router_examples; load_router_examples()"
```

---

## 🎯 Tips

1. **Be specific** - Add variations of the same intent
2. **Cover edge cases** - Typos, slang, formal/informal
3. **Balance intents** - Keep search/chat examples roughly balanced
4. **Test after adding** - Use `python tools/interactive_tester.py`

---

**Questions?** Check `WHERE_IS_EVERYTHING.md` in project root.

