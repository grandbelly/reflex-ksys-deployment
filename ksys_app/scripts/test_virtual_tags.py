"""
Test VirtualTagService - Calculate Virtual Tags and verify results

Run from Docker:
    docker exec reflex-ksys-app python ksys_app/scripts/test_virtual_tags.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ksys_app.db_orm import get_async_session
from ksys_app.services.virtual_tag_service import VirtualTagService
from reflex.utils import console


async def test_virtual_tag_calculation():
    """Test Virtual Tag calculation"""

    console.info("=" * 60)
    console.info("🧪 Testing Virtual Tag Calculation")
    console.info("=" * 60)

    async with get_async_session() as session:
        service = VirtualTagService(session)

        # 1. Get active Virtual Tags
        console.info("\n1️⃣ Loading Virtual Tag definitions...")
        virtual_tags = await service.get_active_virtual_tags()
        console.info(f"   Found {len(virtual_tags)} active Virtual Tags:")
        for tag in virtual_tags:
            console.info(f"   - {tag['tag_name']} ({tag['formula_type']})")

        # 2. Calculate all Virtual Tags
        console.info("\n2️⃣ Calculating Virtual Tag values...")
        results = await service.calculate_all_virtual_tags(time_delta=10.0)

        # 3. Display results
        console.info(f"\n3️⃣ Calculation Results ({len(results)} successful):")
        console.info("-" * 60)

        for result in results:
            value_str = f"{result['value']:.2f}" if result['value'] is not None else "N/A"
            console.info(f"   {result['tag_name']:30s} = {value_str:>10s} {result['unit'] or ''}")

        # 4. Store results
        console.info("\n4️⃣ Storing results to database...")
        await service.store_virtual_tag_values(results)

        console.info("\n" + "=" * 60)
        console.info("✅ Virtual Tag calculation test complete!")
        console.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_virtual_tag_calculation())
