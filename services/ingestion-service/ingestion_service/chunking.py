import re


def split_text(text: str, *, max_words: int = 120) -> list[str]:
    words = re.findall(r"\S+", text)
    return [" ".join(words[start : start + max_words]) for start in range(0, len(words), max_words)]
