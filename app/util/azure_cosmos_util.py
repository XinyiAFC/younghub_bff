from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions


class AzureCosmosUtil:
    def __init__(self):
        self.key_vault_name = "storage-account-01"
        self.secret_name = "younghub-cosmos-master-key"
        self.KVUri = f"https://{self.key_vault_name}.vault.azure.net/"
        self.credential = DefaultAzureCredential()  # Authenticate with Azure

        self.host = 'https://younghub.documents.azure.com:443/'
        self.db_name = 'Article'
        self.container_id = 'List'

    def get_container(self):
        secret_client = SecretClient(vault_url=self.KVUri, credential=self.credential)
        master_key = secret_client.get_secret(self.secret_name).value

        client = cosmos_client.CosmosClient(
            self.host,
            {'masterKey': master_key},
            user_agent="younghub_cosmos",
            user_agent_overwrite=True
        )

        try:
            db = client.get_database_client(self.db_name)
        except exceptions.CosmosHttpResponseError as e:
            print(f'Error accessing database: {e}')
            return None

        try:
            container = db.get_container_client(self.container_id)
            print(f"Container '{self.container_id}' accessed successfully.")
            return container
        except exceptions.CosmosHttpResponseError as e:
            print(f'Error accessing container: {e}')
            return None

    # === 公共入口：可选按频道过滤 / Optional channel filter ===
    def read_article_list(self, channel_id: str | None = None, top: int | None = None):
        container = self.get_container()
        if not container:
            return []

        return self._read_items(container, channel_id=channel_id, top=top)

    # === 读取并显式投影全部需要的字段 / Read + explicit projection ===
    def _read_items(self, container, channel_id: str | None = None, top: int | None = None):
        try:
            if channel_id:
                query = """
                    SELECT
                        c.id, c.ID, c.OrderID, c.Title, c.Subtitle,
                        c.Description, c.DescriptionText, c.ContentURL,
                        c.RegistrationURL, c.Author, c.PictureURL, c.Location,
                        c.StartDate, c.EndDate, c.ContentHTML, c.PublishedAt,
                        c.UpdatedAt, c.SourceURL, c.SourcePostID, c.ContentStatus,
                        c.ContentType, c.FeaturedImageBlobURL, c.SyncVersion
                    FROM c
                    WHERE c.ID = @id
                """
                params = [{"name": "@id", "value": channel_id}]
            else:
                query = """
                    SELECT
                        c.id, c.ID, c.OrderID, c.Title, c.Subtitle,
                        c.Description, c.DescriptionText, c.ContentURL,
                        c.RegistrationURL, c.Author, c.PictureURL, c.Location,
                        c.StartDate, c.EndDate, c.ContentHTML, c.PublishedAt,
                        c.UpdatedAt, c.SourceURL, c.SourcePostID, c.ContentStatus,
                        c.ContentType, c.FeaturedImageBlobURL, c.SyncVersion
                    FROM c
                """
                params = []

            items_iter = container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True  # ✅ 必须：跨分区查询
            )

            result_list = []
            for item in items_iter:
                # 直接把需要的字段返回给前端（缺失的字段给空字符串 / None）
                projected = {
                    "id": item.get("id", ""),
                    "ID": item.get("ID", ""),
                    "OrderID": item.get("OrderID"),
                    "Title": item.get("Title", ""),
                    "Subtitle": item.get("Subtitle", ""),
                    "Description": item.get("Description", ""),
                    "ContentURL": item.get("ContentURL", ""),
                    "Author": item.get("Author", ""),
                    "PictureURL": item.get("PictureURL", ""),
                    "Location": item.get("Location", ""),
                    "StartDate": item.get("StartDate", ""),
                    "EndDate": item.get("EndDate", ""),
                    "ContentHTML": item.get("ContentHTML"),
                    "PublishedAt": item.get("PublishedAt"),
                    "UpdatedAt": item.get("UpdatedAt"),
                    "SourceURL": item.get("SourceURL"),
                    "SourcePostID": item.get("SourcePostID"),
                    "ContentStatus": item.get("ContentStatus"),
                    "ContentType": item.get("ContentType"),
                    "FeaturedImageBlobURL": item.get("FeaturedImageBlobURL"),
                    "SyncVersion": item.get("SyncVersion")
                }
                result_list.append(projected)

            if top is not None and top > 0:
                result_list = result_list[:top]

            return result_list

        except exceptions.CosmosHttpResponseError as e:
            print(f'Failed to read items: {e}')
            return []
