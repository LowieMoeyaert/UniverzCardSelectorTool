def extract_card_network(card_name):
    """Extracts the card network from the card name."""
    networks = {
        "Visa": 1,
        "Mastercard": 2,
        "Amex": 3,  # American Express
        "Diners Club": 4,
        "Discover": 5,
        "JCB": 6,
        "UnionPay": 7
    }

    for network, network_id in networks.items():
        if network.lower() in card_name.lower():
            return str(network_id)  # Return as string to match CSV format

    return "0"  # Default to 0 if no match is found
