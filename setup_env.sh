{
    # Generate the random key and encode it in base64
    random_key=$(head -c 50 /dev/urandom | base64)

    # Create or update the .env file
    echo
    echo '### Do not set this as "True" in Production###'
    echo 'DEBUG="False"'
    echo
    echo ALLOWED_HOSTS=\[\]
    echo
    echo BOT_NAME=\"\"
    echo DISCORD_TOKEN=\"\"
    echo YT_API_KEY=\"\"
    echo SECRET_KEY=\"$random_key\"
    echo MUSIC_CHANNEL=\"\"
    echo HALLOWEEN_CHANNEL=\"\"
    echo
    echo 'SESSION_COOKIE_SECURE="True"'
    echo 'CSRF_COOKIE_SECURE="True"'
    echo 'SECURE_SSL_REDIRECT="True"'
    echo 'WHITENOISE_USE_FINDERS="True"'
    echo
    echo DATABASE_ENGINE=\"\"
    echo DATABASE_NAME=\"\"
    echo DATABASE_USER=\"\"
    echo DATABASE_PASSWORD=\"\"
    echo DATABASE_HOST=\"\"
    echo DATABASE_PORT=\"\"
    echo
    echo
    echo
    echo LOGGING_CLASS=\"\"
    echo LOGGING_LEVEL=\"\"
} >> .env
