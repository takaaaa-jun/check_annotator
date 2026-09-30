FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

# ベースイメージに残っている署名エラーのYarnリポジトリを削除する。
# Node.jsはdevcontainer.jsonのFeatureでインストールするため、
# このリポジトリは使用しない。
RUN rm -f \
        /etc/apt/sources.list.d/yarn.list \
        /etc/apt/sources.list.d/yarn.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        git \
        default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/check_annotator

CMD ["sleep", "infinity"]