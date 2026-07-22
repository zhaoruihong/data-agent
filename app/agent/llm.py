from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config

llm_zhipu = init_chat_model(model=app_config.llm_zhipu.model_name,
                      model_provider="openai",
                      api_key=app_config.llm_zhipu.api_key,
                      base_url=app_config.llm_zhipu.base_url,
                      temperature=0)


if __name__ == '__main__':
    for chunk in llm_zhipu.stream("What is the meaning of life?"):
        print(chunk.text)
