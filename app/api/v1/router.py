from fastapi import APIRouter

from app.api.v1.albums import router as albums_router
from app.api.v1.artists import router as artists_router
from app.api.v1.auth import router as auth_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.history import router as history_router
from app.api.v1.playlists import router as playlists_router
from app.api.v1.search import router as search_router
from app.api.v1.songs import router as songs_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.users import router as users_router
from app.api.v1.home import router as home_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(songs_router)
api_router.include_router(search_router)
api_router.include_router(playlists_router)
api_router.include_router(favorites_router)
api_router.include_router(history_router)
api_router.include_router(artists_router)
api_router.include_router(albums_router)
api_router.include_router(uploads_router)
api_router.include_router(home_router)