def determine_islamic_status(card_name, url, is_islamic_source):
    """
    Determines if the card is Islamic.
    - If the URL contains 'islamic-banking' → return 1.
    - If the card name contains 'Islamic' → return 1.
    - Otherwise, return is_islamic_source (default = 0).
    """
    if "islamic-banking" in url.lower() or "islamic" or "islami" or "islam" in card_name.lower():
        return 1
    return is_islamic_source