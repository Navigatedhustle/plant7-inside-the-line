# Enable the local Cosmos vision model

No token should be sent in chat, included in screenshots, or committed to Git. The helper reads the ignored project `.env` file and prints only access status. It downloads a tiny pinned configuration file, not model weights.

1. Open https://huggingface.co/nvidia/Cosmos-Reason2-8B in a browser.
2. Sign into the same personal Hugging Face account that created your token. Access approval belongs to that account.
3. Find the access form on the model card. Read the NVIDIA terms and information sharing notice, fill in the requested details, and submit if you agree.
4. If the page shows a pending request, wait for the publisher's decision. Creating another token does not grant model approval. If the request is rejected, contact the publisher through its documented support channel.
5. If the page says access is granted but the verifier still fails, open https://huggingface.co/settings/tokens and edit the token's permissions. A fine grained token needs read access to the gated model. Hugging Face may show a permission for reading public gated repositories you can access. Write permissions are unnecessary.
6. If you created a replacement token, save it from the station terminal with:

   ```bash
   cd ~/plant7-investigator
   .venv/bin/python scripts/set_hf_token.py
   ```

   Paste only the `hf_...` token at the hidden prompt, then press Enter. Do not type `HF_TOKEN=` at that prompt. The helper preserves other `.env` entries and sets file permissions to 0600.

7. Verify access:

   ```bash
   .venv/bin/python scripts/verify_hf_access.py
   ```

   Continue only when it prints `SUCCESS`. A valid token and model approval are separate checks. HTTP 403 with “not in the authorized list” means the account still lacks model approval. An approved account can also be blocked by a token with insufficient permissions.

Sources: [Cosmos model access form and license](https://huggingface.co/nvidia/Cosmos-Reason2-8B), [Hugging Face gated model access](https://huggingface.co/docs/hub/models-gated), [Hugging Face token permissions](https://huggingface.co/docs/hub/security-tokens).
