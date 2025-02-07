def test_imports():
    """Test that we can import the required modules."""
    from artist_manager_agent.team_management import PaymentMethod, PaymentStatus, PaymentRequest
    from artist_manager_agent.main import ArtistManagerBot
    
    assert PaymentMethod is not None
    assert PaymentStatus is not None
    assert PaymentRequest is not None
    assert ArtistManagerBot is not None
