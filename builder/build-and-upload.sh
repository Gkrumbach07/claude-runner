#!/bin/bash
set -e

echo "🚀 Building and uploading static site: $SITE_NAME"

# Download source
case "$SOURCE_TYPE" in
    "git")
        echo "📥 Cloning Git repository: $GIT_REPOSITORY"
        git clone --depth 1 --branch "${GIT_BRANCH:-main}" "$GIT_REPOSITORY" source
        if [[ -n "$GIT_PATH" && "$GIT_PATH" != "." ]]; then
            mv "source/$GIT_PATH"/* . || true
            mv "source/$GIT_PATH"/.[^.]* . 2>/dev/null || true
        else
            mv source/* . || true
            mv source/.[^.]* . 2>/dev/null || true
        fi
        rm -rf source
        ;;
    "docker")
        echo "📥 Extracting from Docker image: $DOCKER_IMAGE"
        # This would need docker-in-docker setup
        echo "Docker source not implemented yet"
        exit 1
        ;;
    "url")
        echo "📥 Downloading from URL: $URL_ARCHIVE"
        wget -O archive.zip "$URL_ARCHIVE"
        unzip -q archive.zip
        rm archive.zip
        ;;
esac

# Build if enabled
if [[ "$BUILD_ENABLED" == "true" ]]; then
    echo "🔨 Building site..."
    if [[ -f "package.json" ]]; then
        npm ci
    fi
    eval "$BUILD_COMMAND"
    
    # Move built files
    if [[ -d "$BUILD_OUTPUT_DIR" ]]; then
        cp -r "$BUILD_OUTPUT_DIR"/* /tmp/dist/ || true
    else
        echo "❌ Build output directory $BUILD_OUTPUT_DIR not found"
        exit 1
    fi
else
    echo "📂 Copying source files directly"
    mkdir -p /tmp/dist
    cp -r ./* /tmp/dist/ || true
fi

# Ensure index.html exists
if [[ ! -f "/tmp/dist/index.html" ]]; then
    echo "📄 Creating default index.html"
    cat > /tmp/dist/index.html << EOF
<!DOCTYPE html>
<html>
<head><title>$SITE_NAME</title></head>
<body>
    <h1>🚀 $SITE_NAME</h1>
    <p>Your static site is now live!</p>
    <p>Deployed: $(date)</p>
</body>
</html>
EOF
fi

# Upload to MinIO
echo "☁️ Uploading to MinIO..."
mc alias set myminio "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"

cd /tmp/dist
zip -r ../site.zip . -x "*.DS_Store" "*.git*"

# Mirror to MinIO (overwrites completely)
mc mirror --overwrite --remove . "myminio/sites/$SITE_NAME/"

echo "✅ Upload completed successfully!"
echo "🌐 Site available at: https://$SITE_NAME.sites.apps.example.com/"