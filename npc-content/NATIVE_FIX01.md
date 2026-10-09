# Native NPC test compilation fix

Run 37976126440 stopped compiling dda_artisan_services_test.cpp because Catch cannot decompose operator||. Wrap the complete completion assertion in parentheses; short circuiting and the checked behavior remain intact.

Previous run 37969811286 successfully compiled game and tests and passed all five dialogue/item/switch test cases (29 assertions). The new measurement/faction tests still need their replacement Windows run.

Local patch application and the 55-topic adapter validation passed.
