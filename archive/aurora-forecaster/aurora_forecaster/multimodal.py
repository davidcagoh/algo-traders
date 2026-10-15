"""
Aurora's own `generate(text_inputs=...)` convenience path calls
`.squeeze(0)` on the tokenizer output (aurora/ts_generation_mixin.py), which
collapses the batch dimension whenever batch size is 1 — our case, since we
forecast one asset at a time. That crashes downstream BERT encoding with
"not enough values to unpack (expected 2, got 1)". Confirmed via
scripts/multimodal_smoke_test.py 2026-08-06.

Workaround: tokenize ourselves and pass text_input_ids/text_attention_mask/
text_token_type_ids directly — generate() only hits the buggy squeeze path
when text_inputs is not None, so pre-tokenized tensors bypass it entirely.
"""

from aurora.ts_generation_mixin import TSGenerationMixin

DEFAULT_MAX_TEXT_LENGTH = 125


def tokenize_text_context(text: str | list[str], max_length: int = DEFAULT_MAX_TEXT_LENGTH):
    texts = [text] if isinstance(text, str) else text
    return TSGenerationMixin.tokenizer(
        texts,
        padding="max_length",
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
