import httpx
import asyncio

BASE_URL = "http://localhost:8000"

async def test_order_permissions():
    """ทดสอบ permissions ของ orders"""
    
    async with httpx.AsyncClient() as client:
        print("=== ทดสอบ Order Permissions ===\n")
        
        # Login as user
        print("1. Login as john_doe (user)")
        user_response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={"username": "john_doe", "password": "admin123"}
        )
        user_token = user_response.json()["access_token"]
        print(f"Got user token\n")
        
        # Login as admin
        print("2. Login as admin")
        admin_response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        admin_token = admin_response.json()["access_token"]
        print(f"Got admin token\n")
        
        # Test 1: User get all orders (should see only own)
        print("3. User ขอดู orders ทั้งหมด")
        response = await client.get(
            f"{BASE_URL}/api/v1/orders",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        user_orders = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Found {len(user_orders)} orders (เฉพาะของตัวเอง)\n")
        
        # Test 2: Admin get all orders
        print("4. Admin ขอดู orders ทั้งหมด")
        response = await client.get(
            f"{BASE_URL}/api/v1/orders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        all_orders = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Found {len(all_orders)} orders (ทั้งหมดในระบบ)\n")
        
        # Test 3: User try to update order status (should fail)
        if all_orders:
            order_id = all_orders[0]["id"]
            print(f"5. User พยายามเปลี่ยนสถานะ order {order_id}")
            response = await client.patch(
                f"{BASE_URL}/api/v1/orders/{order_id}/status",
                json={"status": "completed"},
                headers={"Authorization": f"Bearer {user_token}"}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 403:
                print(f"Correctly forbidden: {response.json()['detail']}\n")
            else:
                print(f"Should be 403 but got {response.status_code}\n")
        
        # Test 4: Admin update order status (should work)
        if all_orders:
            order_id = all_orders[0]["id"]
            print(f"6. Admin เปลี่ยนสถานะ order {order_id}")
            response = await client.patch(
                f"{BASE_URL}/api/v1/orders/{order_id}/status",
                json={"status": "processing"},
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Successfully updated\n")
            else:
                print(f"Failed: {response.text}\n")

if __name__ == "__main__":
    asyncio.run(test_order_permissions())