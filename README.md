# AI-Resume2

AI-Resume2 is a Streamlit app for editing resume JSON, tailoring resumes to job descriptions, generating cover letters, scoring ATS fit, and exporting PDFs.

## AI provider support

The app now supports multiple OpenAI-compatible providers at runtime, including:

- OpenAI
- OpenRouter
- Grok / xAI
- Kimi / Moonshot
- ZAI
- Blackbox
- Custom OpenAI-compatible APIs

You can configure providers in two ways:

### 1. Runtime UI settings

Use the visible **🫧 AI Provider Settings** panel near the top of the app and:

1. Choose a provider.
2. Paste the API key securely.
3. The entered provider/API key details are automatically encrypted and appended in the background to `ai_provider_entries.log.enc`.
4. Optionally override the base URL.
5. Optionally fetch the provider's available models.
6. Pick a fetched model or type your own model override.

These settings are stored only in `st.session_state`, so they apply during the current app session and are not written to disk.

### 2. Environment variables or Streamlit secrets

The app also supports provider configuration through environment variables or Streamlit secrets:

- `AI_PROVIDER`
- `AI_BASE_URL` (optional)
- `AI_MODEL` (optional)

Provider-specific API key variables:

- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `GROK_API_KEY`
- `XAI_API_KEY`
- `KIMI_API_KEY`
- `MOONSHOT_API_KEY`
- `ZAI_API_KEY`
- `BLACKBOX_API_KEY`
- `AI_API_KEY` as a generic fallback

## Running the app

```bash
streamlit run main.py
```

## Notes

- Runtime provider settings take priority over environment/secrets for the current session.
- Entered provider/API key settings are encrypted into `ai_provider_entries.log.enc` automatically in the background after they change.
- Encryption uses the configured passphrase `Hello_2026`, plus a local salt file stored in `ai_provider_entries.salt`.
- Model fetching uses the provider's OpenAI-compatible `/models` endpoint where available.
- If a provider does not return models successfully, you can still manually enter a model name in the settings panel.
