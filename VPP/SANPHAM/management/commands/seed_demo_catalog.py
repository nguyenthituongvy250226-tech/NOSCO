from pathlib import Path
from typing import Any, TypedDict

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from SANPHAM.models import (
    BienTheSanPham,
    DanhMucSanPham,
    HinhAnhSanPham,
    SanPham,
    ThuongHieu,
)


DATABASE = "sanpham"

class ProductSeed(TypedDict):
    id: str
    name: str
    category: str
    brand: str
    description: str
    variant: tuple[str, str, str, str, int]
    images: list[str]


CATEGORIES: list[tuple[str, str, str]] = [
    ("DM001", "Dụng cụ học tập", "Bút, bút chì và vật dụng phục vụ học tập."),
    ("DM002", "Sổ và giấy", "Sổ tay, giấy ghi chú và các sản phẩm giấy."),
    ("DM003", "Văn phòng phẩm", "Vật dụng thiết yếu cho học tập và văn phòng."),
    ("DM004", "Dụng cụ sáng tạo", "Dụng cụ hỗ trợ vẽ, thủ công và sáng tạo."),
]

BRANDS: list[tuple[str, str]] = [
    ("THIENLONG", "Thiên Long"),
    ("DELI", "Deli"),
    ("NOSCO", "NOSCO"),
]

PRODUCTS: list[ProductSeed] = [
    {
        "id": "SP001",
        "name": "Bút bi Thiên Long",
        "category": "DM003",
        "brand": "THIENLONG",
        "description": "Bút bi mực xanh, nét viết êm, phù hợp ghi chép hằng ngày.",
        "variant": ("BT001", "Xanh", "0.5mm", "5000.00", 100),
        "images": ["butviet.png"],
    },
    {
        "id": "SP002",
        "name": "Sổ tay A5",
        "category": "DM002",
        "brand": "NOSCO",
        "description": "Sổ tay khổ A5 bìa cứng, phù hợp ghi chú và lập kế hoạch.",
        "variant": ("BT002", "Xanh navy", "A5", "25000.00", 50),
        "images": ["product-notebook.jpg", "product-notebook1.jpg"],
    },
    {
        "id": "SP003",
        "name": "Bút highlight pastel",
        "category": "DM001",
        "brand": "NOSCO",
        "description": "Bút màu pastel dùng đánh dấu nội dung và trang trí ghi chú.",
        "variant": ("BT003", "Vàng pastel", "Tiêu chuẩn", "12000.00", 30),
        "images": ["product-pastel-pens.jpg", "product-pastel-pens1.jpg"],
    },
    {
        "id": "SP004",
        "name": "Bút chì HB Deli",
        "category": "DM001",
        "brand": "DELI",
        "description": "Bút chì HB dùng cho học tập, phác thảo và ghi chép.",
        "variant": ("BT004", "Đen", "HB", "3000.00", 80),
        "images": ["product-pencils.jpg", "product-pencils1.jpg"],
    },
    {
        "id": "SP005",
        "name": "Giấy ghi chú nhiều màu",
        "category": "DM002",
        "brand": "THIENLONG",
        "description": "Giấy ghi chú nhiều màu, tiện đánh dấu và nhắc việc.",
        "variant": ("BT005", "Nhiều màu", "5 màu", "8000.00", 60),
        "images": ["product-sticky-notes.jpg", "product-sticky-notes1.jpg"],
    },
    {
        "id": "SP006",
        "name": "Bộ dụng cụ học toán",
        "category": "DM004",
        "brand": "THIENLONG",
        "description": "Bộ dụng cụ hình học cơ bản hỗ trợ học tập và vẽ kỹ thuật.",
        "variant": ("BT006", "Nhiều màu", "Bộ cơ bản", "45000.00", 20),
        "images": ["dungcuhoctap.png"],
    },
]


class Command(BaseCommand):
    help = "Thêm danh mục, sản phẩm và ảnh mẫu vào cơ sở dữ liệu SANPHAM."

    def handle(self, *args, **options):
        source_root = Path(settings.BASE_DIR) / "static" / "images"
        image_paths: set[str] = {
            image
            for product in PRODUCTS
            for image in product["images"]
        }
        missing_images = sorted(
            image for image in image_paths if not (source_root / image).is_file()
        )
        if missing_images:
            raise CommandError(
                "Missing sample images in static/images: "
                + ", ".join(missing_images)
            )

        storage = FileSystemStorage(location=settings.MEDIA_ROOT)
        with transaction.atomic(using=DATABASE):
            categories = {
                category_id: self._get_or_create(
                    DanhMucSanPham,
                    category_id,
                    {
                        "ten_danh_muc": name,
                        "mo_ta": description,
                    },
                )
                for category_id, name, description in CATEGORIES
            }
            brands = {
                brand_id: self._get_or_create(
                    ThuongHieu,
                    brand_id,
                    {"ten_thuong_hieu": name, "mo_ta": ""},
                )
                for brand_id, name in BRANDS
            }

            for product_data in PRODUCTS:
                product = self._get_or_create(
                    SanPham,
                    product_data["id"],
                    {
                        "danh_muc": categories[product_data["category"]],
                        "thuong_hieu": brands[product_data["brand"]],
                        "ten_san_pham": product_data["name"],
                        "mo_ta": product_data["description"],
                        "trang_thai_ban": "Đang bán",
                    },
                )
                variant_id, color, size, price, stock = product_data["variant"]
                variant = self._get_or_create(
                    BienTheSanPham,
                    variant_id,
                    {
                        "san_pham": product,
                        "mau_sac": color,
                        "kich_thuoc": size,
                        "gia_ban": price,
                        "so_luong_ton": stock,
                    },
                )

                for index, filename in enumerate(product_data["images"], start=1):
                    image_id = f"IMG{product_data['id'][-3:]}{index:02d}"
                    relative_path = f"products/demo/{product_data['id'].lower()}-{filename}"
                    if not storage.exists(relative_path):
                        with (source_root / filename).open("rb") as source:
                            storage.save(relative_path, source)
                    self._get_or_create(
                        HinhAnhSanPham,
                        image_id,
                        {
                            "bien_the": variant,
                            "duong_dan_anh": relative_path,
                            "thu_tu_hien_thi": index - 1,
                            "anh_dai_dien": index == 1,
                        },
                    )

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(CATEGORIES)} categories, {len(BRANDS)} brands, "
            f"{len(PRODUCTS)} products and "
            f"{sum(len(p['images']) for p in PRODUCTS)} images."
        ))

    @staticmethod
    def _get_or_create(model, object_id: str, defaults: dict[str, Any]):
        instance, created = model.objects.using(DATABASE).get_or_create(
            pk=object_id,
            defaults=defaults,
        )
        if created:
            return instance

        for field, expected in defaults.items():
            model_field = model._meta.get_field(field)
            actual = getattr(instance, f"{field}_id", None) if model_field.is_relation else getattr(instance, field)
            expected_value = (
                getattr(expected, "pk", expected)
                if model_field.is_relation
                else model_field.to_python(expected)
            )
            if actual != expected_value:
                raise CommandError(
                    f"ID {object_id} already exists with different "
                    f"{model.__name__}.{field} data; not overwriting."
                )
        return instance
