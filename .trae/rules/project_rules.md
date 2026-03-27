该项目所有生成的代码都需要遵循以下规则：
- 所有代码，文本，示例，注释等都需要使用英文
- 所有代码，文本，示例，注释等都需要使用 UTF-8 编码
- 生成的所有python代码都要符合 [PEP8](符合 [PEP8](URL_ADDRESS.python.org/dev/peps/pep-0008/) 规范
- 生成的类代码中，如果没有特别指明，都不要随意print信息，仅当调试时可以打印一些调试信息，调试完成需要删除掉
- 生成的类，都要在其下的main函数中进行测试，用assert进行断言，需要打印出case的输入，expected output和actual output, 且一个case出错后，不能停止，需要继续执行下去，直到所有case都执行完毕