"""
Unit tests for BYD Cockpit CLI / REPL interface (scripts/byd_cockpit_cli.py).
"""

from scripts.byd_cockpit_cli import BYDCockpitCLI


def test_byd_cockpit_cli_scenario():
    cli = BYDCockpitCLI()

    # 1. Hardware demo command
    resp_demo = cli.handle_command("/demo rotate_screen portrait")
    assert "竖屏" in resp_demo or "自适应旋转" in resp_demo

    # 2. Vehicle comparison command
    resp_comp = cli.handle_command("/compare 海豹")
    assert "海豹" in resp_comp or "对比" in resp_comp

    # 3. Finance quote command
    resp_fin = cli.handle_command("/finance")
    assert "免息" in resp_fin or "首付" in resp_fin

    # 4. Test drive scheduling command
    resp_td = cli.handle_command("/testdrive")
    assert "预约" in resp_td
    assert "事务单号" in resp_td

    # 5. Inventory check command
    resp_inv = cli.handle_command("/inventory")
    assert "现车" in resp_inv

    # 6. Reversible transaction rollback
    resp_rb = cli.handle_command("/rollback")
    assert "事务可逆回滚" in resp_rb
    assert "成功撤销" in resp_rb

    # 7. Natural dialogue utterance
    resp_dialogue = cli.handle_message("你好，请介绍一下我们坐的这台展车")
    assert "汉" in resp_dialogue or "比亚迪" in resp_dialogue

    # 8. Parameterized test drive command
    resp_td_custom = cli.handle_command("/testdrive 王总 13988888888 周日上午10点 汉EV")
    assert "王总" in resp_td_custom
    assert "周日上午10点" in resp_td_custom

    # 9. Parameterized inventory command
    resp_inv_ocean = cli.handle_command("/inventory 海洋")
    assert "现车" in resp_inv_ocean
    assert "SEAL" in resp_inv_ocean or "Dolphin" in resp_inv_ocean

    # 10. Unsupported demo feature error reporting
    resp_demo_err = cli.handle_command("/demo unsupported_feature")
    assert "❌" in resp_demo_err or "失败" in resp_demo_err or "座舱硬件" in resp_demo_err
