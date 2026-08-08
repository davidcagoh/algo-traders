import torch

from aurora_forecaster.multimodal import tokenize_text_context


def test_tokenize_text_context_preserves_batch_dimension():
    tokenized = tokenize_text_context("Bitcoin ETF inflows slow.", max_length=32)

    assert tokenized["input_ids"].shape == (1, 32)
    assert tokenized["attention_mask"].shape == (1, 32)
    assert tokenized["token_type_ids"].shape == (1, 32)


def test_tokenize_text_context_handles_batch_of_texts():
    tokenized = tokenize_text_context(
        ["Bitcoin ETF inflows slow.", "SPY drifts higher."], max_length=32
    )

    assert tokenized["input_ids"].shape == (2, 32)


def test_tokenize_text_context_dtype_is_long():
    tokenized = tokenize_text_context("Bitcoin ETF inflows slow.", max_length=32)

    assert tokenized["input_ids"].dtype == torch.long
