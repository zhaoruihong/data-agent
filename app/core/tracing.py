from app.conf.app_config import app_config
from app.core.log import logger


def setup_langfuse():
    """
    初始化 Langfuse 回调处理器，并注册到 LangChain 全局回调管理器。
    当 langfuse.enabled = false 时，此函数为空操作，不引入任何副作用。
    """
    if not app_config.langfuse.enabled:
        logger.info("Langfuse tracing 未启用，跳过初始化")
        return

    try:
        from langfuse.callback import CallbackHandler
        from langchain.callbacks.manager import get_openai_callback
        import langchain_core.callbacks

        handler = CallbackHandler(
            public_key=app_config.langfuse.public_key,
            secret_key=app_config.langfuse.secret_key,
            host=app_config.langfuse.host,
        )

        # 注册为 LangChain 全局回调，所有 chain/LLM 调用自动上报，无需改 node 代码
        langchain_core.callbacks.manager._configure_inheritable_callbacks(
            local_callbacks=None,
            inherit_config=True,
            local_inheritable_callbacks=[handler],
            local_tags=None,
            local_metadata=None,
            local_run_name=None,
        )

        # 更简洁的方式：直接设置环境变量让 LangChain 自动 pick up Langfuse
        import os
        os.environ["LANGFUSE_PUBLIC_KEY"] = app_config.langfuse.public_key
        os.environ["LANGFUSE_SECRET_KEY"] = app_config.langfuse.secret_key
        os.environ["LANGFUSE_HOST"] = app_config.langfuse.host

        # 开启 LangChain 的 tracing（v2 协议，Langfuse 兼容）
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "true"  # 异步上报，不阻塞请求

        logger.info(f"Langfuse tracing 已启用，上报地址: {app_config.langfuse.host}")

    except ImportError:
        logger.warning("langfuse 包未安装，请执行 `uv add langfuse` 后重启服务")
    except Exception as e:
        logger.error(f"Langfuse 初始化失败: {e}")
