def test_imports():
    """Test that we can import the required modules."""
    from artist_manager_agent.agent import (
        ArtistManagerAgent,
        ArtistProfile,
        Contract,
        Event,
        FinancialRecord,
        Task
    )
    
    assert ArtistManagerAgent is not None
    assert ArtistProfile is not None
    assert Contract is not None
    assert Event is not None
    assert FinancialRecord is not None
    assert Task is not None 