# asphyxia-to-mysql

用于将氧无数据文件迁移到 MySQL 中的脚本。只支持 SDVX。

## 前提

已基于 [bemaniutils](https://github.com/DragonMinded/bemaniutils) 创建好 MySQL 数据表。

已安装好 Python 依赖：

```shell
pip install -r requirements.txt

```

## 运行方法

```shell
./asyphyxia-to-mysql -d path/to/your/asphyxia/savedata -r refid -c path/to/your/config.yaml --card cardid --pcbid pcbid
```

参数说明：

- `-d`: 氧无数据记录路径。
- `-r`: 氧无数据记录的唯一标识符, 即 refid（可在氧无 dashboard 与数据文件中找到）。
- `-c`: MySQL 配置文件路径（模板位于 `config/mysql.yaml`）。
- `--card`: 你的 card ID。
- `--pcbid`: 你的 PCBID。

**所有参数都必须指定**。

P.S. 以上参数不放入 `config.yaml` 中，是为了方便批量处理。