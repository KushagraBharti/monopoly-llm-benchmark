import monopoly_arena
import monopoly_api


def test_api_shims_delegate_to_arena() -> None:
    import monopoly_api.action_validation as api_action_validation
    import monopoly_api.llm_runner as api_llm_runner
    import monopoly_api.paths as api_paths
    import monopoly_api.player_config as api_player_config
    import monopoly_api.prompting as api_prompting
    import monopoly_api.schema_registry as api_schema_registry

    import monopoly_arena.action_validation as arena_action_validation
    import monopoly_arena.llm_runner as arena_llm_runner
    import monopoly_arena.paths as arena_paths
    import monopoly_arena.player_config as arena_player_config
    import monopoly_arena.prompting as arena_prompting
    import monopoly_arena.schema_registry as arena_schema_registry

    assert monopoly_api is not None
    assert monopoly_arena is not None

    assert api_action_validation.validate_action_payload is arena_action_validation.validate_action_payload
    assert api_llm_runner.LlmRunner is arena_llm_runner.LlmRunner
    assert api_schema_registry.get_schema is arena_schema_registry.get_schema
    assert api_schema_registry.get_schema_registry is arena_schema_registry.get_schema_registry
    assert api_paths.resolve_repo_root is arena_paths.resolve_repo_root
    assert api_player_config.PlayerConfig is arena_player_config.PlayerConfig
    assert api_player_config.build_player_configs is arena_player_config.build_player_configs
    assert api_prompting.PromptMemory is arena_prompting.PromptMemory
    assert api_prompting.build_prompt_bundle is arena_prompting.build_prompt_bundle

