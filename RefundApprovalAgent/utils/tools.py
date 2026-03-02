# 导入日志模块，用于记录程序运行过程中的信息
import logging
# 导入支持并发的日志文件处理器，避免多进程写入日志时发生冲突
from concurrent_log_handler import ConcurrentRotatingFileHandler
# 导入类型提示：Callable表示可调用对象（函数）
from typing import Callable
# 导入LangChain的基础工具类和工具创建装饰器
from langchain_core.tools import BaseTool, tool as create_tool
# 导入可运行配置类，用于传递运行时配置信息
from langchain_core.runnables import RunnableConfig
# 导入类型字典，用于定义结构化的字典类型
from typing import TypedDict
# 导入中断函数，用于在工作流中请求人工介入
from langgraph.types import interrupt
# 再次导入tool装饰器（实际上与上面的create_tool相同）
from langchain_core.tools import tool
# 从配置模块导入配置类
from .config import Config
# 导入日期时间处理模块和时间差模块
from datetime import datetime, timedelta
# 导入随机数生成模块
import random



# 配置日志
# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)
# 设置日志级别为DEBUG，记录详细的调试信息
logger.setLevel(logging.DEBUG)
# 清空现有的日志处理器列表
logger.handlers = []
# 创建支持并发的循环文件处理器
handler = ConcurrentRotatingFileHandler(
    # 日志文件路径
    Config.LOG_FILE,
    # 单个日志文件的最大字节数
    maxBytes=Config.MAX_BYTES,
    # 保留的备份日志文件数量
    backupCount=Config.BACKUP_COUNT
)
# 设置处理器的日志级别为DEBUG
handler.setLevel(logging.DEBUG)
# 设置日志格式：时间 - 模块名 - 级别 - 消息
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
# 将处理器添加到日志记录器
logger.addHandler(handler)


# 定义类型
# 定义操作请求的类型结构
class ActionRequest(TypedDict):
    # 操作名称（工具名称）
    action: str
    # 操作参数字典
    args: dict


# 定义人工中断配置的类型结构
class HumanInterruptConfig(TypedDict):
    # 是否允许忽略此次审核
    allow_ignore: bool
    # 是否允许审核人提供自定义响应
    allow_respond: bool
    # 是否允许审核人编辑参数
    allow_edit: bool
    # 是否允许审核人直接批准
    allow_accept: bool


# 定义人工中断请求的完整结构
class HumanInterrupt(TypedDict):
    # 要审核的操作请求
    action_request: ActionRequest
    # 审核配置选项
    config: HumanInterruptConfig
    # 可选的描述信息，显示给审核人员
    description: str | None


# ==================== 模拟数据库 ====================

# 模拟订单数据
# 创建一个字典存储模拟的订单数据，键为订单号
MOCK_ORDERS = {
    # 订单1：已发货的蓝牙耳机订单
    "ORD20180101001": {
        # 订单编号
        "order_id": "ORD20180101001",
        # 客户姓名
        "customer_name": "张小明",
        # 商品名称
        "product_name": "无线蓝牙耳机",
        # 订单金额
        "order_amount": 299.00,
        # 订单状态
        "order_status": "已发货",
        # 下单时间
        "order_time": "2018-01-01 10:30:00",
        # 收货地址
        "shipping_address": "香港九龙旺角xx街xx号",
        # 物流跟踪状态
        "tracking_status": "运输中",
        # 预计送达日期
        "estimated_delivery": "2018-01-05"
    },
    # 订单2：已签收的运动鞋订单
    "ORD20180102002": {
        # 订单编号
        "order_id": "ORD20180102002",
        # 客户姓名
        "customer_name": "李美华",
        # 商品名称
        "product_name": "运动跑鞋",
        # 订单金额
        "order_amount": 599.00,
        # 订单状态
        "order_status": "已签收",
        # 下单时间
        "order_time": "2018-01-02 14:20:00",
        # 收货地址
        "shipping_address": "香港港岛中环yy路yy号",
        # 物流跟踪状态
        "tracking_status": "已送达",
        # 预计送达日期
        "estimated_delivery": "2018-01-04"
    },
    # 订单3：待发货的智能手环订单
    "ORD20180103003": {
        # 订单编号
        "order_id": "ORD20180103003",
        # 客户姓名
        "customer_name": "王大力",
        # 商品名称
        "product_name": "智能手环",
        # 订单金额
        "order_amount": 89.00,
        # 订单状态
        "order_status": "待发货",
        # 下单时间
        "order_time": "2018-01-03 09:15:00",
        # 收货地址
        "shipping_address": "香港新界沙田zz街zz号",
        # 物流跟踪状态
        "tracking_status": "待出库",
        # 预计送达日期
        "estimated_delivery": "2018-01-06"
    },
    # 订单4：配送中的电脑背包订单
    "ORD20180104004": {
        # 订单编号
        "order_id": "ORD20180104004",
        # 客户姓名
        "customer_name": "陈小芳",
        # 商品名称
        "product_name": "电脑背包",
        # 订单金额
        "order_amount": 158.00,
        # 订单状态
        "order_status": "配送中",
        # 下单时间
        "order_time": "2018-01-04 11:00:00",
        # 收货地址
        "shipping_address": "香港九龙尖沙咀aa路aa号",
        # 物流跟踪状态
        "tracking_status": "派送中",
        # 预计送达日期
        "estimated_delivery": "2018-01-04"
    },
    # 订单5：已发货的机械键盘订单
    "ORD20180104005": {
        # 订单编号
        "order_id": "ORD20180104005",
        # 客户姓名
        "customer_name": "刘志强",
        # 商品名称
        "product_name": "机械键盘",
        # 订单金额
        "order_amount": 899.00,
        # 订单状态
        "order_status": "已发货",
        # 下单时间
        "order_time": "2018-01-04 15:30:00",
        # 收货地址
        "shipping_address": "香港港岛铜锣湾bb街bb号",
        # 物流跟踪状态
        "tracking_status": "运输中",
        # 预计送达日期
        "estimated_delivery": "2018-01-06"
    }
}

# 模拟退款理由列表
# 定义常见的退款原因，供用户选择
REFUND_REASONS = [
    # 商品存在质量缺陷
    "商品质量问题",
    # 收到的商品与页面描述不一致
    "商品与描述不符",
    # 商品尺寸不符合需求
    "尺寸不合适",
    # 主观原因不想要了
    "不喜欢/不想要了",
    # 商品在运输过程中损坏
    "收到商品破损",
    # 商家发错了商品
    "发错货",
    # 物流配送速度太慢
    "物流太慢",
    # 购买后商品降价了
    "价格降价了"
]


# ==================== 工具函数 ====================

# 从模拟数据库中查询订单信息
def get_mock_order(order_id: str):
    """从模拟数据库获取订单信息"""
    # 使用字典的get方法查询订单，如果不存在返回None
    return MOCK_ORDERS.get(order_id, None)


# 生成唯一的退款单号
def generate_refund_number():
    """生成退款单号"""
    # 获取当前时间戳，格式为年月日时分秒
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    # 生成4位随机数作为后缀
    random_suffix = random.randint(1000, 9999)
    # 组合成退款单号：REF + 时间戳 + 随机后缀
    return f"REF{timestamp}{random_suffix}"


# ==================== 人工审查功能 ====================

# 为工具添加人工审查环节的异步函数
async def add_human_in_the_loop(
        # 要包装的原始工具（函数或BaseTool对象）
        tool: Callable | BaseTool,
        *,
        # 人工审查的配置选项，默认为None
        interrupt_config: HumanInterruptConfig = None,
) -> BaseTool:
    """为工具添加人工审查功能"""
    # 如果传入的不是BaseTool对象，则将其转换为工具
    if not isinstance(tool, BaseTool):
        # 使用create_tool装饰器将普通函数转换为工具
        tool = create_tool(tool)

    # 使用装饰器创建一个新的工具，保留原工具的名称、描述和参数模式
    @create_tool(
        # 工具名称
        tool.name,
        # 工具描述
        description=tool.description,
        # 工具参数的JSON Schema
        args_schema=tool.args_schema
    )
    # 定义包装后的异步工具函数
    async def call_tool_with_interrupt(config: RunnableConfig, **tool_input):
        # 从工具输入参数中获取订单号，默认为空字符串
        order_id = tool_input.get('order_id', '')
        # 从模拟数据库中查询订单信息
        order_info = get_mock_order(order_id)

        # 如果找到了订单信息
        if order_info:
            # 构建格式化的审核信息展示给审核人员
            display_info = (
                f"【退款审核】\n"
                # 分隔线
                f"━━━━━━━━━━━━━━━━━━━━\n"
                # 显示订单号
                f"订单号: {order_info['order_id']}\n"
                # 显示客户姓名
                f"用户: {order_info['customer_name']}\n"
                # 显示商品名称
                f"商品: {order_info['product_name']}\n"
                # 显示订单原金额
                f"订单金额: ¥{order_info['order_amount']}\n"
                # 显示申请退款金额
                f"退款金额: ¥{tool_input.get('refund_amount', 0)}\n"
                # 显示退款原因
                f"退款原因: {tool_input.get('refund_reason', 'N/A')}\n"
                # 显示订单当前状态
                f"订单状态: {order_info['order_status']}\n"
                # 分隔线
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                # 提示审核人员可以执行的操作
                f"是否批准退款?\n"
                # 输入yes批准
                f"输入 'yes' 批准退款\n"
                # 输入no拒绝
                f"输入 'no' 拒绝退款\n"
                # 输入edit修改金额
                f"输入 'edit' 修改退款金额\n"
                # 输入response提供自定义意见
                f"输入 'response' 提供处理意见"
            )
        # 如果没有找到订单信息
        else:
            # 构建警告信息展示给审核人员
            display_info = (
                f"【退款审核】\n"
                # 显示订单号
                f"订单号: {order_id}\n"
                # 显示退款金额
                f"退款金额: ¥{tool_input.get('refund_amount', 0)}\n"
                # 显示退款原因
                f"退款原因: {tool_input.get('refund_reason', 'N/A')}\n\n"
                # 警告：未找到订单
                f"⚠️ 警告: 未找到订单信息\n\n"
                # 提示审核人员可以执行的操作
                f"是否批准退款?\n"
                # 输入yes批准
                f"输入 'yes' 批准退款\n"
                # 输入no拒绝
                f"输入 'no' 拒绝退款\n"
                # 输入edit修改金额
                f"输入 'edit' 修改退款金额\n"
                # 输入response提供自定义意见
                f"输入 'response' 提供处理意见"
            )

        # 构建人工中断请求对象
        request: HumanInterrupt = {
            # 操作请求：包含工具名称和参数
            "action_request": {
                # 工具名称
                "action": tool.name,
                # 工具参数
                "args": tool_input
            },
            # 审核配置选项
            "config": interrupt_config,
            # 展示给审核人员的描述信息
            "description": display_info,
        }

        # 调用interrupt函数暂停执行，等待人工审核响应
        response = interrupt(request)
        # 记录审核结果到日志
        logger.info(f"审核结果: {response}")

        # 如果审核人员选择批准（accept）
        if response["type"] == "accept":
            # 记录批准信息
            logger.info("退款已批准")
            # 使用try-except捕获可能的异常
            try:
                # 调用原始工具执行退款操作
                tool_response = await tool.ainvoke(input=tool_input)
                # 记录退款执行结果
                logger.info(f"退款结果: {tool_response}")
            # 如果执行过程中发生异常
            except Exception as e:
                # 记录错误信息
                logger.error(f"退款处理失败: {e}")
                # 返回失败消息
                tool_response = f"退款失败: {str(e)}"

        # 如果审核人员选择编辑（edit）
        elif response["type"] == "edit":
            # 记录编辑信息
            logger.info("参数已修改")
            # 使用修改后的参数替换原参数
            tool_input = response["args"]["args"]
            # 使用try-except捕获可能的异常
            try:
                # 使用新参数调用原始工具
                tool_response = await tool.ainvoke(input=tool_input)
                # 记录退款执行结果
                logger.info(f"退款结果: {tool_response}")
            # 如果执行过程中发生异常
            except Exception as e:
                # 记录错误信息
                logger.error(f"退款处理失败: {e}")
                # 返回失败消息
                tool_response = f"退款失败: {str(e)}"

        # 如果审核人员选择拒绝（reject）
        elif response["type"] == "reject":
            # 记录拒绝信息
            logger.info("退款被拒绝")
            # 构建拒绝消息，包含拒绝原因（如果提供）
            tool_response = f'退款申请被拒绝。拒绝原因: {response.get("reason", "未提供原因")}'

        # 如果审核人员提供自定义响应（response）
        elif response["type"] == "response":
            # 记录审核人提供意见
            logger.info("审核人提供处理意见")
            # 直接使用审核人的响应作为工具返回值
            tool_response = response["args"]

        # 如果响应类型不在预期范围内
        else:
            # 抛出值错误异常
            raise ValueError(f"不支持的响应类型: {response['type']}")

        # 返回工具执行结果
        return tool_response

    # 返回包装后的工具
    return call_tool_with_interrupt


# ==================== 业务工具定义 ====================

# 获取所有业务工具的异步函数
async def get_tools():
    """获取电商退款系统的工具集"""

    # 1. 处理大额退款(需要主管审核)
    # 使用tool装饰器定义工具，指定工具名称和描述
    @tool("process_large_refund", description="处理大额退款(金额>500元,需要主管审核)")
    # 定义处理大额退款的异步函数
    async def process_large_refund(
            # 订单号参数
            order_id: str,
            # 退款金额参数
            refund_amount: float,
            # 退款原因参数
            refund_reason: str
    ):
        """
        处理大额退款申请

        Args:
            order_id: 订单号
            refund_amount: 退款金额
            refund_reason: 退款原因

        Returns:
            退款处理结果
        """
        # 查询订单信息
        order_info = get_mock_order(order_id)
        # 如果订单不存在
        if not order_info:
            # 返回错误消息
            return f"错误: 订单号 {order_id} 不存在"

        # 生成退款单号
        refund_number = generate_refund_number()
        # 计算预计到账日期（当前时间加3-5天）
        arrival_date = (datetime.now() + timedelta(days=random.randint(3, 5))).strftime('%Y-%m-%d')

        # 返回格式化的退款成功消息
        return f"""
✅ 退款已成功处理
━━━━━━━━━━━━━━━━━━━━
退款单号: {refund_number}
订单号: {order_info['order_id']}
用户: {order_info['customer_name']}
商品: {order_info['product_name']}
订单金额: ¥{order_info['order_amount']}
退款金额: ¥{refund_amount}
退款原因: {refund_reason}
审核级别: 主管审核
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
预计到账: {arrival_date}
━━━━━━━━━━━━━━━━━━━━
"""

    # 2. 处理中额退款(需要客服审核)
    # 使用tool装饰器定义工具
    @tool("process_medium_refund", description="处理中等金额退款(201-500元,需要客服审核)")
    # 定义处理中额退款的异步函数
    async def process_medium_refund(
            # 订单号参数
            order_id: str,
            # 退款金额参数
            refund_amount: float,
            # 退款原因参数
            refund_reason: str
    ):
        """
        处理中等金额退款申请

        Args:
            order_id: 订单号
            refund_amount: 退款金额
            refund_reason: 退款原因

        Returns:
            退款处理结果
        """
        # 查询订单信息
        order_info = get_mock_order(order_id)
        # 如果订单不存在
        if not order_info:
            # 返回错误消息
            return f"错误: 订单号 {order_id} 不存在"

        # 生成退款单号
        refund_number = generate_refund_number()
        # 计算预计到账日期（当前时间加1-3天）
        arrival_date = (datetime.now() + timedelta(days=random.randint(1, 3))).strftime('%Y-%m-%d')

        # 返回格式化的退款成功消息
        return f"""
✅ 退款已成功处理
━━━━━━━━━━━━━━━━━━━━
退款单号: {refund_number}
订单号: {order_info['order_id']}
用户: {order_info['customer_name']}
商品: {order_info['product_name']}
订单金额: ¥{order_info['order_amount']}
退款金额: ¥{refund_amount}
退款原因: {refund_reason}
审核级别: 客服审核
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
预计到账: {arrival_date}
━━━━━━━━━━━━━━━━━━━━
"""

    # 3. 处理小额退款(自动批准,无需审核)
    # 使用tool装饰器定义工具
    @tool("process_small_refund", description="处理小额退款(≤200元,自动批准)")
    # 定义处理小额退款的异步函数
    async def process_small_refund(
            # 订单号参数
            order_id: str,
            # 退款金额参数
            refund_amount: float,
            # 退款原因参数
            refund_reason: str
    ):
        """
        处理小额退款申请(自动批准)

        Args:
            order_id: 订单号
            refund_amount: 退款金额
            refund_reason: 退款原因

        Returns:
            退款处理结果
        """
        # 查询订单信息
        order_info = get_mock_order(order_id)
        # 如果订单不存在
        if not order_info:
            # 返回错误消息
            return f"错误: 订单号 {order_id} 不存在"

        # 生成退款单号
        refund_number = generate_refund_number()
        # 计算预计到账小时数（12-24小时内）
        arrival_hours = random.randint(12, 24)

        # 返回格式化的自动批准消息
        return f"""
✅ 退款已自动批准
━━━━━━━━━━━━━━━━━━━━
退款单号: {refund_number}
订单号: {order_info['order_id']}
用户: {order_info['customer_name']}
商品: {order_info['product_name']}
订单金额: ¥{order_info['order_amount']}
退款金额: ¥{refund_amount}
退款原因: {refund_reason}
审核级别: 自动批准
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
预计到账: {arrival_hours}小时内
━━━━━━━━━━━━━━━━━━━━
"""

    # 4. 查询订单信息
    # 使用tool装饰器定义工具
    @tool("query_order_info", description="查询订单详细信息")
    # 定义查询订单的异步函数
    async def query_order_info(order_id: str):
        """
        查询订单详细信息

        Args:
            order_id: 订单号

        Returns:
            订单详细信息
        """
        # 查询订单信息
        order_info = get_mock_order(order_id)

        # 如果订单不存在
        if not order_info:
            # 返回所有可用的订单号提示
            # 将所有订单号组合成列表格式
            available_orders = "\n".join([f"- {oid}" for oid in MOCK_ORDERS.keys()])
            # 返回订单不存在的提示信息
            return f"""
❌ 订单不存在
━━━━━━━━━━━━━━━━━━━━
订单号: {order_id}
状态: 未找到该订单

💡 可用的模拟订单号:
{available_orders}
━━━━━━━━━━━━━━━━━━━━
"""

        # 返回格式化的订单详细信息
        return f"""
📦 订单信息
━━━━━━━━━━━━━━━━━━━━
订单号: {order_info['order_id']}
用户姓名: {order_info['customer_name']}
商品名称: {order_info['product_name']}
订单金额: ¥{order_info['order_amount']}
订单状态: {order_info['order_status']}
下单时间: {order_info['order_time']}
收货地址: {order_info['shipping_address']}
物流状态: {order_info['tracking_status']}
预计送达: {order_info['estimated_delivery']}
━━━━━━━━━━━━━━━━━━━━
"""

    # 5. 查询可用退款理由
    # 使用tool装饰器定义工具
    @tool("list_refund_reasons", description="查看所有可用的退款理由")
    # 定义查询退款理由的异步函数
    async def list_refund_reasons():
        """
        查看所有可用的退款理由

        Returns:
            退款理由列表
        """
        # 将所有退款理由格式化为编号列表
        reasons_list = "\n".join([f"{i + 1}. {reason}" for i, reason in enumerate(REFUND_REASONS)])
        # 返回格式化的退款理由列表
        return f"""
📋 可用退款理由
━━━━━━━━━━━━━━━━━━━━
{reasons_list}
━━━━━━━━━━━━━━━━━━━━
💡 提示: 选择合适的退款理由可以加快审核速度
"""

    # 定义审核配置
    # 大额退款需要主管审核
    # 创建主管审核的配置对象
    high_amount_config = HumanInterruptConfig(
        # 不允许忽略审核
        allow_ignore=False,
        # 允许提供自定义响应
        allow_respond=True,
        # 允许编辑参数
        allow_edit=True,
        # 允许直接批准
        allow_accept=True
    )

    # 中额退款需要客服审核
    # 创建客服审核的配置对象
    medium_amount_config = HumanInterruptConfig(
        # 不允许忽略审核
        allow_ignore=False,
        # 允许提供自定义响应
        allow_respond=True,
        # 允许编辑参数
        allow_edit=True,
        # 允许直接批准
        allow_accept=True
    )

    # 构建工具列表
    tools = [
        # 大额退款需要主管审核
        # 为大额退款工具添加人工审查环节
        await add_human_in_the_loop(
            # 大额退款工具
            process_large_refund,
            # 使用主管审核配置
            interrupt_config=high_amount_config
        ),
        # 中额退款需要客服审核
        # 为中额退款工具添加人工审查环节
        await add_human_in_the_loop(
            # 中额退款工具
            process_medium_refund,
            # 使用客服审核配置
            interrupt_config=medium_amount_config
        ),
        # 小额退款自动批准
        # 直接添加小额退款工具，无需审核
        process_small_refund,
        # 查询订单工具不需要审核
        # 直接添加查询订单工具
        query_order_info,
        # 查询退款理由不需要审核
        # 直接添加查询退款理由工具
        list_refund_reasons
    ]

    # 返回完整的工具列表
    return tools
