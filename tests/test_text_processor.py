import pytest
from hunyuan_podcast.text_processor import TextProcessor


def test_extract_roles_filters_binary_and_content_types():
    tp = TextProcessor()
    # 模拟文本包含二进制残留和 Content_Types 以及一个合法角色
    binary_like = "(WbNRYe\x1fg\x0cOSR\x01\x08^[\x10bvsQvR)"
    text = f"[{binary_like}]\n[Content_Types]\n[角色A] 你好，欢迎回来！\n"

    roles = tp.extract_roles(text)
    # 期望只保留合法的角色 '角色A'
    assert '角色A' in roles
    assert 'Content_Types' not in roles
    assert all(r.isprintable() for r in roles)


def test_parse_role_text_basic():
    tp = TextProcessor()
    text = "[角色A]（兴奋地）：今天天气真好！\n[角色B]（思考状）：是的，我们来聊聊AI。"
    dialogues = tp.parse_role_text(text)
    assert isinstance(dialogues, list)
    assert len(dialogues) == 2
    assert dialogues[0][0] == '角色A'
    assert '今天天气真好' in dialogues[0][1]
    assert dialogues[1][0] == '角色B'


if __name__ == '__main__':
    pytest.main([__file__])
