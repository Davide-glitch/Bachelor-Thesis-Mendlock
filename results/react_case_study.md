# React 18 + TypeScript Real-Application Case Study

| Scenario                 | Mutation Type                   | Mode        | Status                   | Attempts | Correct | False Commit | Blocked HTTP | Latency (ms) |
|--------------------------|---------------------------------|-------------|--------------------------|----------|---------|--------------|--------------|--------------|
| react-catalog-4070       | context + reorder + label_shift | gate        | ABSTAINED_LOW_CONFIDENCE |        0 |       0 |            0 |            0 |        113.2 |
| react-catalog-4070       | context + reorder + label_shift | verify      | ABSTAINED_LOW_CONFIDENCE |        0 |       0 |            0 |            0 |        109.0 |
| react-catalog-4070       | context + reorder + label_shift | verify_topk | HEALED_VERIFIED          |        1 |       1 |            0 |            0 |        200.1 |
| react-checkout-order     | id_churn + class_churn + decoy  | gate        | HEALED_UNVERIFIED        |        1 |       1 |            0 |            0 |        232.9 |
| react-checkout-order     | id_churn + class_churn + decoy  | verify      | HEALED_VERIFIED          |        1 |       1 |            0 |            0 |        241.1 |
| react-checkout-order     | id_churn + class_churn + decoy  | verify_topk | HEALED_VERIFIED          |        1 |       1 |            0 |            0 |        209.2 |
| react-wire-transfer      | restyle + dom_wrap              | gate        | HEALED_UNVERIFIED        |        1 |       1 |            0 |            0 |        271.2 |
| react-wire-transfer      | restyle + dom_wrap              | verify      | HEALED_VERIFIED          |        1 |       1 |            0 |            0 |        291.2 |
| react-wire-transfer      | restyle + dom_wrap              | verify_topk | HEALED_VERIFIED          |        1 |       1 |            0 |            0 |        258.7 |
| react-security-policy    | tag_change + label_shift        | gate        | ABSTAINED_LOW_CONFIDENCE |        0 |       0 |            0 |            0 |         96.5 |
| react-security-policy    | tag_change + label_shift        | verify      | ABSTAINED_LOW_CONFIDENCE |        0 |       0 |            0 |            0 |        110.2 |
| react-security-policy    | tag_change + label_shift        | verify_topk | HEALED_VERIFIED          |        1 |       1 |            0 |            0 |        420.2 |
| react-legacy-xml-removed | removed (target deleted in v2)  | gate        | ABSTAINED_LOW_CONFIDENCE |        0 |       0 |            0 |            0 |         86.8 |
| react-legacy-xml-removed | removed (target deleted in v2)  | verify      | ABSTAINED_LOW_CONFIDENCE |        0 |       0 |            0 |            0 |        107.6 |
| react-legacy-xml-removed | removed (target deleted in v2)  | verify_topk | ABSTAINED_LOW_CONFIDENCE |        0 |       0 |            0 |            0 |        103.3 |
