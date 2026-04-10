import asyncio
from src.routers.intent_router import get_semantic_router, force_reload_routers

async def main():
    print("Getting router pt...")
    router = get_semantic_router('pt')
    
    print("Testing pokopia...")
    res = router("pokopia")
    print(f"Pokopia -> {res.name if res else None}")

    print("Forcing reload...")
    force_reload_routers()
    
    router2 = get_semantic_router('pt')
    res2 = router2("pokopia")
    print(f"Pokopia after reload -> {res2.name if res2 else None}")

asyncio.run(main())
