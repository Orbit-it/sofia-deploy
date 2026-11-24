[Unit]
Description=Sofia-managed app (__APP_NAME__)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=__APP_USER__
Group=__APP_GROUP__
WorkingDirectory=__APP_DIR__
EnvironmentFile=__ENV_FILE__
ExecStart=__START_EXEC__
Restart=always
RestartSec=5
TimeoutStopSec=20
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
