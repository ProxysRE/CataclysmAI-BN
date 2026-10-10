# Artisan shop policy audit

Pinned DDA: c19e95bc96d27d8bef8e2e246a63cd4cd6f89974.

Both CODY_MILLER and JAY_RUCKERS define one rigid shopkeeper_item_group. src/npc.cpp samples rigid groups once with item_group::items_from. Value-based groups loop until their value budget is spent. src/npc_class.cpp defaults restock_interval to six days. The earlier port reduced both groups to BN strings, losing rigid sampling. This checkpoint restores that property and the interval without changing other BN classes.

shopkeeper_consumption_rates: basic_shop_rates is present in both source NPC classes, but is not read by this revision's npc_class loader. Its current consumers are trade zones: npc::shop_restock calls consume_items_in_zones with elapsed time and distributes new stock via distribute_items_to_npc_zones. The historical string is retained as metadata, not implemented with invented consumption behavior. Trade-zone migration remains a tracked dependency.

https://github.com/CleverRaven/Cataclysm-DDA/blob/c19e95bc96d27d8bef8e2e246a63cd4cd6f89974/src/npc.cpp
https://github.com/CleverRaven/Cataclysm-DDA/blob/c19e95bc96d27d8bef8e2e246a63cd4cd6f89974/src/npc_class.cpp
