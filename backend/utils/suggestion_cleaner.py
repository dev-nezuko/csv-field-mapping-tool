def clean_suggestion(suggestion: str) -> str:
    """Keep the mapping notes a person edited and drop the model's earlier rationale."""
    suggestion = suggestion.replace('\\n', '\n')
    rationale = suggestion.find('Rationale:')
    return suggestion if rationale == -1 else suggestion[:rationale]
