def test_imports():
    """Test that we can import the required modules."""
    from artist_manager_agent.team_management import PaymentMethod, TeamManager
    
    assert PaymentMethod is not None
    assert TeamManager is not None 