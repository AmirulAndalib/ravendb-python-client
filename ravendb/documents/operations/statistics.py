from __future__ import annotations

import datetime
import json
from typing import Optional, Dict, List, TYPE_CHECKING, Any

import requests

from ravendb.documents.indexes.definitions import IndexPriority, IndexLockMode, IndexType, IndexSourceType, IndexState
from ravendb.documents.operations.definitions import MaintenanceOperation
from ravendb.http.raven_command import RavenCommand
from ravendb.http.server_node import ServerNode
from ravendb.tools.utils import Size, Utils

if TYPE_CHECKING:
    from ravendb.documents.conventions import DocumentConventions


class DatabaseStatistics:
    def __init__(
        self,
        last_doc_etag: int = None,
        last_database_etag: int = None,
        count_of_indexes: int = None,
        count_of_documents: int = None,
        count_of_revision_documents: int = None,
        count_of_documents_conflicts: int = None,
        count_of_tombstones: int = None,
        count_of_conflicts: int = None,
        count_of_attachments: int = None,
        count_of_unique_attachments: int = None,
        count_of_counter_entries: int = None,
        count_of_time_series_segments: int = None,
        indexes: List[IndexInformation] = None,
        database_change_vector: str = None,
        database_id: str = None,
        is_64_bit: bool = None,
        pager: str = None,
        last_indexing_time: datetime.datetime = None,
        size_on_disk: Size = None,
        temp_buffers_size_on_disk: Size = None,
        number_of_transaction_merger_queue_operations: int = None,
    ):
        self.last_doc_etag = last_doc_etag
        self.last_database_etag = last_database_etag
        self.count_of_indexes = count_of_indexes
        self.count_of_documents = count_of_documents
        self.count_of_revision_documents = count_of_revision_documents
        self.count_of_documents_conflicts = count_of_documents_conflicts
        self.count_of_tombstones = count_of_tombstones
        self.count_of_conflicts = count_of_conflicts
        self.count_of_attachments = count_of_attachments
        self.count_of_unique_attachments = count_of_unique_attachments
        self.count_of_counter_entries = count_of_counter_entries
        self.count_of_time_series_segments = count_of_time_series_segments

        self.indexes = indexes

        self.database_change_vector = database_change_vector
        self.database_id = database_id
        self.is_64_bit = is_64_bit
        self.pager = pager
        self.last_indexing_time = last_indexing_time
        self.size_on_disk = size_on_disk
        self.temp_buffers_size_on_disk = temp_buffers_size_on_disk
        self.number_of_transaction_merger_queue_operations = number_of_transaction_merger_queue_operations

    @property
    def stale_indexes(self) -> List[IndexInformation]:
        return list(filter(lambda x: x.stale, self.indexes))

    @classmethod
    def from_json(cls, json_dict) -> DatabaseStatistics:
        return cls(
            json_dict.get("LastDocEtag", None),
            json_dict.get("LastDatabaseEtag", None),
            json_dict.get("CountOfIndexes", None),
            json_dict.get("CountOfDocuments", None),
            json_dict.get("CountOfRevisionDocuments", None),
            json_dict.get("CountOfDocumentsConflicts", None),
            json_dict.get("CountOfTombstones", None),
            json_dict.get("CountOfConflicts", None),
            json_dict.get("CountOfAttachments", None),
            json_dict.get("CountOfUniqueAttachments", None),
            json_dict.get("CountOfCounterEntries", None),
            json_dict.get("CountOfTimeSeriesSegments", None),
            [IndexInformation.from_json(x) for x in json_dict["Indexes"]] if "Indexes" in json_dict else None,
            json_dict.get("DatabaseChangeVector", None),
            json_dict.get("DatabaseId", None),
            json_dict.get("Is64Bit", None),
            json_dict.get("Pager", None),
            Utils.string_to_datetime(json_dict["LastIndexingTime"]) if json_dict.get("LastIndexingTime") else None,
            Size.from_json(json_dict.get("SizeOnDisk", None)),
            Size.from_json(json_dict.get("TempBuffersSizeOnDisk", None)),
            json_dict.get("NumberOfTransactionMergerQueueOperations", None),
        )


class GetStatisticsOperation(MaintenanceOperation[DatabaseStatistics]):
    def __init__(self, debug_tag: str = None, node_tag: str = None):
        self.debug_tag = debug_tag
        self.node_tag = node_tag

    def get_command(self, conventions: "DocumentConventions") -> _GetStatisticsCommand[DatabaseStatistics]:
        return self._GetStatisticsCommand(self.debug_tag, self.node_tag)

    class _GetStatisticsCommand(RavenCommand[DatabaseStatistics]):
        def __init__(self, debug_tag: Optional[str] = None, node_tag: Optional[str] = None):
            super().__init__(dict)
            self.debug_tag = debug_tag
            self.node_tag = node_tag

        def create_request(self, node: ServerNode) -> requests.Request:
            return requests.Request(
                "GET",
                f"{node.url}/databases/{node.database}"
                f"/stats{f'?{self.debug_tag}' if self.debug_tag is not None else ''}",
            )

        def set_response(self, response: str, from_cache: bool) -> None:
            self.result = DatabaseStatistics.from_json(json.loads(response))

        def is_read_request(self) -> bool:
            return True


class CollectionStatistics:
    def __init__(
        self,
        count_of_documents: Optional[int] = None,
        count_of_conflicts: Optional[int] = None,
        collections: Optional[Dict[str, int]] = None,
    ):
        self.count_of_documents = count_of_documents
        self.count_of_conflicts = count_of_conflicts
        self.collections = collections

    @classmethod
    def from_json(cls, json_dict: dict) -> CollectionStatistics:
        return cls(json_dict["CountOfDocuments"], json_dict["CountOfConflicts"], json_dict["Collections"])


class GetCollectionStatisticsOperation(MaintenanceOperation[CollectionStatistics]):
    def get_command(self, conventions) -> RavenCommand[CollectionStatistics]:
        return self.__GetCollectionStatisticsCommand()

    class __GetCollectionStatisticsCommand(RavenCommand[CollectionStatistics]):
        def __init__(self):
            super().__init__(CollectionStatistics)

        def create_request(self, server_node: ServerNode) -> requests.Request:
            return requests.Request("GET", f"{server_node.url}/databases/{server_node.database}/collections/stats")

        def is_read_request(self) -> bool:
            return True

        def set_response(self, response: str, from_cache: bool) -> None:
            if response is None:
                self._throw_invalid_response()
            self.result = CollectionStatistics.from_json(json.loads(response))


class IndexInformation:
    def __init__(
        self,
        stale: bool = None,
        lock_mode: IndexLockMode = None,
        priority: IndexPriority = None,
        index_type: IndexType = None,
        last_indexing_time: datetime.datetime = None,
        source_type: IndexSourceType = None,
        index_state: IndexState = None,
        name: str = None,
    ):
        self.stale = stale
        self.lock_mode = lock_mode
        self.priority = priority
        self.type = index_type
        self.last_indexing_time: datetime.datetime = last_indexing_time
        self.source_type = source_type
        self.state = index_state
        self.name = name

    @classmethod
    def from_json(cls, json_dict) -> IndexInformation:
        return cls(
            json_dict["IsStale"] if "IsStale" in json_dict else None,
            IndexLockMode(json_dict["LockMode"]),
            IndexPriority(json_dict["Priority"]) if "Priority" in json_dict else None,
            IndexType(json_dict["Type"]) if "Type" in json_dict else None,
            Utils.string_to_datetime(json_dict["LastIndexingTime"]) if "LastIndexingTime" in json_dict else None,
            IndexSourceType(json_dict["SourceType"]) if "SourceType" in json_dict else None,
            IndexState(json_dict["State"]) if "State" in json_dict else None,
            json_dict["Name"] if "Name" in json_dict else None,
        )


class DetailedDatabaseStatistics(DatabaseStatistics):
    def __init__(
        self,
        last_doc_etag: int = None,
        last_database_etag: int = None,
        count_of_indexes: int = None,
        count_of_documents: int = None,
        count_of_revision_documents: int = None,
        count_of_documents_conflicts: int = None,
        count_of_tombstones: int = None,
        count_of_conflicts: int = None,
        count_of_attachments: int = None,
        count_of_unique_attachments: int = None,
        count_of_counter_entries: int = None,
        count_of_time_series_segments: int = None,
        indexes: List[IndexInformation] = None,
        database_change_vector: str = None,
        database_id: str = None,
        is_64_bit: bool = None,
        pager: str = None,
        last_indexing_time: datetime.datetime = None,
        size_on_disk: Size = None,
        temp_buffers_size_on_disk: Size = None,
        number_of_transaction_merger_queue_operations: int = None,
        count_of_identities: int = None,
        count_of_compare_exchange: int = None,
        count_of_compare_exchange_tombstones: int = None,
    ):
        super().__init__(
            last_doc_etag,
            last_database_etag,
            count_of_indexes,
            count_of_documents,
            count_of_revision_documents,
            count_of_documents_conflicts,
            count_of_tombstones,
            count_of_conflicts,
            count_of_attachments,
            count_of_unique_attachments,
            count_of_counter_entries,
            count_of_time_series_segments,
            indexes,
            database_change_vector,
            database_id,
            is_64_bit,
            pager,
            last_indexing_time,
            size_on_disk,
            temp_buffers_size_on_disk,
            number_of_transaction_merger_queue_operations,
        )

        self.count_of_identities = count_of_identities
        self.count_of_compare_exchange = count_of_compare_exchange
        self.count_of_compare_exchange_tombstones = count_of_compare_exchange_tombstones

    @classmethod
    def from_json(cls, json_dict: Dict) -> DetailedDatabaseStatistics:
        database_stats = DatabaseStatistics.from_json(json_dict)

        detailed_database_stats = cls()
        detailed_database_stats.__dict__.update(database_stats.__dict__)

        detailed_database_stats.count_of_identities = json_dict["CountOfIdentities"]
        detailed_database_stats.count_of_compare_exchange = json_dict["CountOfCompareExchange"]
        detailed_database_stats.count_of_compare_exchange_tombstones = json_dict["CountOfCompareExchangeTombstones"]

        return detailed_database_stats


class GetDetailedStatisticsOperation(MaintenanceOperation[DetailedDatabaseStatistics]):
    def __init__(self, debug_tag: str = None):
        self.__debug_tag = debug_tag

    def get_command(self, conventions: "DocumentConventions") -> RavenCommand[DetailedDatabaseStatistics]:
        return self.DetailedDatabaseStatisticsCommand(self.__debug_tag)

    class DetailedDatabaseStatisticsCommand(RavenCommand[DetailedDatabaseStatistics]):
        def __init__(self, debug_tag: str):
            super().__init__(DetailedDatabaseStatistics)
            self.__debug_tag = debug_tag

        def create_request(self, node: ServerNode) -> requests.Request:
            url = f"{node.url}/databases/{node.database}/stats/detailed"
            if self.__debug_tag is not None:
                url += f"?{self.__debug_tag}"

            return requests.Request("GET", url)

        def set_response(self, response: str, from_cache: bool) -> None:
            self.result = DetailedDatabaseStatistics.from_json(json.loads(response))

        def is_read_request(self) -> bool:
            return True


class CollectionDetails:
    def __init__(
        self,
        name: str = None,
        count_of_documents: int = None,
        size: Size = None,
        documents_size: Size = None,
        tombstones_size: Size = None,
        revisions_size: Size = None,
    ):
        self.name = name
        self.count_of_documents = count_of_documents
        self.size = size
        self.documents_size = documents_size
        self.tombstones_size = tombstones_size
        self.revisions_size = revisions_size

    @classmethod
    def from_json(cls, json_dict: Dict[str, Any]) -> CollectionDetails:
        return cls(
            json_dict["Name"],
            json_dict["CountOfDocuments"],
            Size.from_json(json_dict["Size"]),
            Size.from_json(json_dict["DocumentsSize"]),
            Size.from_json(json_dict["TombstonesSize"]),
            Size.from_json(json_dict["RevisionsSize"]),
        )


class DetailedCollectionStatistics:
    def __init__(
        self,
        count_of_documents: int = None,
        count_of_conflicts: int = None,
        collections: Dict[str, CollectionDetails] = None,
    ) -> None:
        self.count_of_documents = count_of_documents
        self.count_of_conflicts = count_of_conflicts
        self.collections = collections

    @classmethod
    def from_json(cls, json_dict: Dict[str, Any]) -> "DetailedCollectionStatistics":
        return cls(
            json_dict["CountOfDocuments"],
            json_dict["CountOfConflicts"],
            {key: CollectionDetails.from_json(value) for key, value in json_dict["Collections"].items()},
        )


class GetDetailedCollectionStatisticsOperation(MaintenanceOperation[DetailedCollectionStatistics]):
    def get_command(
        self, conventions: "DocumentConventions"
    ) -> "GetDetailedCollectionStatisticsOperation.GetDetailedCollectionStatisticsCommand":
        return self.GetDetailedCollectionStatisticsCommand()

    class GetDetailedCollectionStatisticsCommand(RavenCommand[DetailedCollectionStatistics]):
        def __init__(self):
            super().__init__(DetailedCollectionStatistics)

        def is_read_request(self) -> bool:
            return True

        def create_request(self, node: ServerNode) -> requests.Request:
            return requests.Request("GET", f"{node.url}/databases/{node.database}/collections/stats/detailed")

        def set_response(self, response: Optional[str], from_cache: bool) -> None:
            if not response:
                self._throw_invalid_response()

            self.result = DetailedCollectionStatistics.from_json(json.loads(response))
