from youtube_mass_edit.description import MAX_DESCRIPTION_BYTES, Template, validation_errors

ORIGINAL = """\
* Yes, I'm using "No Goods Consume" cheat.
* There isn't enough footage.

# 😘Chosen Playlist Restrictions
* 1️⃣UDB8R - old rules
* ⚔️Sword Only

# 🤔Extra
* 🌐old playlist link

# ⏰Timestamps
00:00 Phase 1
05:57 Phase 2
11:57 Stats/Skills

#hitless #sekiro"""

NEW_SHARED = """\
# 😘Chosen Playlist Restrictions
* 1️⃣UDB8R - new rules

# 🤔Extra
* 🌐new playlist link
"""


def make_template(hashtags: str = "#hitless #sekiro #udb8r") -> Template:
    return Template(
        start_heading="Chosen Playlist Restrictions",
        end_heading="Timestamps",
        shared_block=NEW_SHARED,
        hashtags=hashtags,
    )


def test_replaces_shared_block_and_hashtags_only() -> None:
    assert (
        make_template().rewrite(ORIGINAL)
        == """\
* Yes, I'm using "No Goods Consume" cheat.
* There isn't enough footage.

# 😘Chosen Playlist Restrictions
* 1️⃣UDB8R - new rules

# 🤔Extra
* 🌐new playlist link

# ⏰Timestamps
00:00 Phase 1
05:57 Phase 2
11:57 Stats/Skills

#hitless #sekiro #udb8r"""
    )


def test_rewrite_is_idempotent() -> None:
    template = make_template()
    once = template.rewrite(ORIGINAL)
    assert once is not None
    assert template.rewrite(once) == once


def test_heading_emoji_can_differ() -> None:
    description = ORIGINAL.replace("😘Chosen", "Chosen").replace("⏰Timestamps", "🕒 Timestamps")
    result = make_template().rewrite(description)
    assert result is not None
    assert "new rules" in result
    assert "# 🕒 Timestamps" in result


def test_missing_heading_returns_none() -> None:
    assert make_template().rewrite(ORIGINAL.replace("# ⏰Timestamps", "Timestamps:")) is None
    assert make_template().rewrite("just a plain description") is None


def test_heading_in_intro_is_kept() -> None:
    description = "# My intro heading\n* bullet\n\n" + ORIGINAL
    result = make_template().rewrite(description)
    assert result is not None
    assert result.startswith("# My intro heading\n* bullet\n\n* Yes")


def test_adds_hashtags_when_missing() -> None:
    result = make_template().rewrite(ORIGINAL.removesuffix("\n\n#hitless #sekiro"))
    assert result is not None
    assert result.endswith("11:57 Stats/Skills\n\n#hitless #sekiro #udb8r")


def test_empty_hashtags_removes_line() -> None:
    result = make_template(hashtags="").rewrite(ORIGINAL)
    assert result is not None
    assert result.endswith("11:57 Stats/Skills")


def test_validation() -> None:
    assert validation_errors(ORIGINAL) == []
    assert validation_errors("a <b> c")
    # Each emoji is 4 bytes, so this is under 5000 characters but over 5000 bytes.
    assert validation_errors("😘" * (MAX_DESCRIPTION_BYTES // 4 + 1))
