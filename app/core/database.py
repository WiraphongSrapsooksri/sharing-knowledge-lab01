import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
from app.config import settings

class JSONDatabase:
    """Simple JSON file-based database"""
    
    def __init__(self, filename: str):
        self.data_dir = Path(settings.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.data_dir / filename
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """สร้างไฟล์ถ้ายังไม่มี"""
        if not self.filepath.exists():
            self._write([])
    
    def _read(self) -> List[Dict[str, Any]]:
        """อ่านข้อมูลจากไฟล์"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write(self, data: List[Dict[str, Any]]):
        """เขียนข้อมูลลงไฟล์"""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def get_all(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูลทั้งหมด (async)"""
        await asyncio.sleep(0)  # จำลอง async operation
        return self._read()
    
    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูลตาม ID"""
        data = await self.get_all()
        return next((item for item in data if item.get('id') == id), None)
    
    async def get_by_field(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูลตาม field ใดๆ"""
        data = await self.get_all()
        return next((item for item in data if item.get(field) == value), None)
    
    async def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """สร้างข้อมูลใหม่"""
        data = await self.get_all()
        data.append(item)
        self._write(data)
        return item
    
    async def update(self, id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """อัพเดทข้อมูล"""
        data = await self.get_all()
        for item in data:
            if item.get('id') == id:
                item.update(updates)
                self._write(data)
                return item
        return None
    
    async def delete(self, id: str) -> bool:
        """ลบข้อมูล"""
        data = await self.get_all()
        new_data = [item for item in data if item.get('id') != id]
        if len(new_data) < len(data):
            self._write(new_data)
            return True
        return False
    
    async def filter(self, **conditions) -> List[Dict[str, Any]]:
        """กรองข้อมูลตามเงื่อนไข"""
        data = await self.get_all()
        result = data
        for key, value in conditions.items():
            result = [item for item in result if item.get(key) == value]
        return result