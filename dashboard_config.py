

with_age = [
    {
        "title": "Age",
        "field": "age",
        "visible": True,
        "responsive": 1,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True,
    }
]
warehouse_table_definition = [
    {
        "formatter": "rowSelection",
        "titleFormatter": "rowSelection",
        "align": "center",
        "headerSort": False,
        "vertAlign": "middle",
        "responsive": 1,
    },
    {
        "title": "Created By",
        "field": "created_by",
        "visible": False,
        "responsive": 1,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True
    },
    {
        "title": "Order #",
        "field": "order_num",
        "visible": False,
        "responsive": 1,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True
    },
    {
        "title": "Consignee",
        "field": "consignee",
        "visible": True,
        "responsive": 1,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True
    },
    {
        "title": "Supplier",
        "field": "shipper",
        "visible": True,
        "responsive": 1,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True,
        "width": "10rem"
    },
    {
        "title": "WR#",
        "field": "magic_link",
        "visible": True,
        "responsive": 1,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True,
        "formatter": "link",
        "formatterParams": {
            "labelField": "number",
            "target": "_blank",
        }
    },
    {
        "title": "Date Delivered",
        "field": "created_date",
        "visible": True,
        "responsive": 2,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True,
    },
    {
        "title": "Description",
        "field": "note",
        "visible": True,
        "responsive": 3,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True,
        "width": 300
    },
    {
        "title": "Invoice",
        "field": "invoice",
        "visible": True,
        "responsive": 3,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True
    },
    {
        "title": "Purchase Order",
        "field": "purchase_order",
        "visible": True,
        "responsive": 3,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True
    },

    {
        "title": "Carrier",
        "field": "carrier",
        "visible": False,
        "responsive": 2,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True
    },
    {
        "title": "Tracking Number",
        "field": "tracking_number",
        "visible": True,
        "responsive": 5,
        "compute": False,
        "vertAlign": "middle",
        "selectable": True
    },
]

with_url = [{
    "title": "Laser Order",
    "field": "laser_order",
    "visible": True,
    "responsive": 1,
    "compute": False,
    "vertAlign": "middle",
    "selectable": True,
    "formatter": "link",
    "formatterParams": {
        "labelField": "order_num",
        "target": "_blank",
    }
}
]


menu_items = [
    {
        'name': 'Home',
        'customerName': 'Interport Dashboard',
        'customerLogo': 'rampslogo.png',
        'displayChildItems': False,
        'childItems': [
        ],
        'eventHandler': ''
    },
    {

        'name': 'Warehouse Receipts',
        'displayChildItems': False,
        'icon': 'fa-solid fa-chart-area',
        'childItems': [
            {
                "active": True,
                'displayChildItems': False,
                'icon': 'fa-solid fa-chart-area',
                'childItems': [],
                'eventHandler': '',
                "title": "Unmatched",
                "name": "Unmatched",
                "archive": True,
                "countries": [

                    {
                        'id': 62,
                        'name': 'Trinidad',
                        'label': 'Trinidad',
                        'active': True,
                        'changed': 1,
                        'dataEndpoint': '/pending-warehouse-receipts',
                        'create_order_button': True,
                        "initialSort": [
                            {
                                "column": "age",
                                "dir": "desc"
                            },
                            {
                                "column": "created_date",
                                "dir": "desc"
                            }
                        ],
                        "initialFilter": [],
                        "tableDefinition":  warehouse_table_definition + with_age
                    },

                ]
            },

            {
                "active": False,
                'displayChildItems': False,
                'icon': 'fa-solid fa-chart-area',
                'childItems': [],
                'eventHandler': '',
                "title": "Matched",
                "name": "Matched",
                "archive": True,
                "countries": [
                    {
                        'id': 63,
                        'name': 'Trinidad',
                        'label': 'Trinidad',
                        'active': True,
                        'changed': 1,
                        'dataEndpoint': '/matched-warehouse-receipts',
                        'update_order_button': True,
                        "initialSort": [
                            {
                                "column": "age",
                                "dir": "desc"
                            },
                            {
                                "column": "created_date",
                                "dir": "desc"
                            }
                        ],
                        "initialFilter": [],
                        "tableDefinition": warehouse_table_definition + with_age + with_url
                    },

                ]
            },
            {
                "active": False,
                'displayChildItems': False,
                'icon': 'fa-solid fa-chart-area',
                'childItems': [],
                'eventHandler': '',
                "title": "Linked",
                "name": "Linked",
                "archive": True,
                "countries": [
                    {
                        'id': 64,
                        'name': 'Trinidad',
                        'label': 'Trinidad',
                        'active': True,
                        'changed': 1,
                        'dataEndpoint': '/linked-warehouse-receipts',
                        "initialSort": [
                            {
                                "column": "created_date",
                                "dir": "desc"
                            }
                        ],
                        "initialFilter": [],
                        "tableDefinition": warehouse_table_definition + with_url
                    },

                ]
            },

        ],
    },
    {

        'name': 'Consignees',
        'displayChildItems': False,
        'icon': 'fa-solid fa-chart-area',
        'childItems': [
            {
                "active": False,
                'displayChildItems': False,
                'icon': 'fa-solid fa-chart-area',
                'childItems': [],
                'eventHandler': '',
                "title": "All",
                "name": "All",
                "archive": True,

                "countries": [

                    {
                        "actions": [{
                                'endpoint': '/consignee/email',
                                'label': 'Update Email',
                                'name': 'consignee_update_email'
                        }],
                        'id': 'all-consignees',
                        'name': 'All',
                        'label': 'All',
                        'active': True,
                        'changed': 1,
                        'dataEndpoint': '/consignees',
                        "initialSort": [],
                        "initialFilter": [],
                        "tableDefinition":  [
                            {
                                "title": "Name",
                                "field": "contact_name",
                                "visible": True,
                                "responsive": 1,
                                "compute": False,
                                "vertAlign": "middle",
                                "selectable": True
                            },
                            {
                                "title": "Email",
                                "field": "email",
                                "visible": True,
                                "responsive": 1,
                                "compute": False,
                                "vertAlign": "middle",
                                "selectable": True
                            },
                        ]
                    },

                ]
            },
        ],
    },
    {
        'name': 'Logout',
        'displayChildItems': False,
        'icon': 'fa-solid fa-right-from-bracket',
        'childItems': [],
        'eventHandler': 'logout'
    }
]
