
Feature: Probabilistic ranking married with deterministic policy

  Scenario: Embargo filters a high-scoring supplier
    Given supplier S1 is embargoed and supplier S2 is not
    And rank_suppliers for Product P returns [S1(score=0.92), S2(score=0.90)]
    When an order (supplier mode) is inserted with one item P qty 5 need_by in 10 days
    Then the order's supplier should be S2
    And there should be a SysSupplierReq row with both S1 and S2 in top_n
