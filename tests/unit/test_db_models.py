"""TestDbModels."""

from napps.kytos.flow_manager.db.models import FlowDoc


class TestDbModels:
    """TestDbModels."""

    def test_flow_doct(self) -> None:
        """Test FlowDoc."""
        flow_dict = {
            "priority": 100,
            "match": {"in_port": 11, "dl_vlan": 3503, "dl_type": 2048, "nw_proto": 6},
            "instructions": [
                {
                    "instruction_type": "apply_actions",
                    "actions": [{"action_type": "push_int"}],
                },
                {"instruction_type": "goto_table", "table_id": 2},
            ],
        }
        data = {
            "switch": "00:00:00:00:00:00:00:01",
            "flow_id": "1",
            "id": "0",
            "flow": flow_dict,
        }
        flow_doc = FlowDoc(**data)
        assert flow_doc
        assert flow_doc.flow.instructions == flow_dict["instructions"]
