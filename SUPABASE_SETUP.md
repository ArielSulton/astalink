# Supabase Setup - status koneksi saat ini

Terakhir dicek: 2026-07-03 05:32 WIB.

## Kesimpulan cepat

Supabase project saat ini **hidup**:

- Project ref: `myehfjbgpykyekfrjczl`
- REST endpoint: OK (`/rest/v1/` membalas `HTTP 200` dengan anon key)
- Auth endpoint: OK (`/auth/v1/settings` membalas `HTTP 200` dengan anon key)
- Backend lokal: OK (`http://localhost:8010/api/v1/health` membalas `HTTP 200`)
- Frontend lokal: OK (`http://localhost:3001/login` membalas `HTTP 200`)

Masalah yang masih ada bukan project Supabase mati, tapi konfigurasi backend belum lengkap untuk fitur penuh.

## Masalah aktif

0. Frontend pernah berjalan dengan project ref lama.

   Root cause error signup:

   ```text
   TypeError: Failed to fetch
   at supabase.auth.signUp(...)
   ```

   Frontend container sebelumnya masih memakai:

   ```text
   NEXT_PUBLIC_SUPABASE_URL=https://tkzboygwdumwepqjfchx.supabase.co
   ```

   Ref lama itu sudah tidak resolve DNS. Container frontend sudah di-recreate dan sekarang memakai:

   ```text
   NEXT_PUBLIC_SUPABASE_URL=https://myehfjbgpykyekfrjczl.supabase.co
   ```

   Jika browser masih error, lakukan hard refresh / clear site cache untuk `localhost:3001`.

1. `SUPABASE_SERVICE_ROLE_KEY` kosong di `.env` host dan container.

   Dampak: fitur backend yang memakai `get_admin_client()` akan gagal, termasuk audit log, approvals, PIN, upload dokumen legal, dan beberapa persistensi agent.

2. Key publik Supabase salah tipe.

   `.env` sekarang mengisi `SUPABASE_ANON_KEY` dan `NEXT_PUBLIC_SUPABASE_ANON_KEY` dengan key bertipe `sb_secret`.

   Jangan expose `sb_secret_*` ke frontend. Untuk browser, gunakan salah satu:

   - `sb_publishable_*` dari Supabase Dashboard, atau
   - anon public JWT key jika dashboard masih memakai format lama.

   `sb_secret_*` hanya boleh dipakai server-side dan tidak boleh masuk ke variable `NEXT_PUBLIC_*`.

3. `.env` host dan container backend berjalan tidak sama sebelum recreate.

   `.env` host sekarang memakai:

   ```text
   SUPABASE_DB_URL host: db.myehfjbgpykyekfrjczl.supabase.co:5432
   ```

   Container backend yang sedang berjalan memakai:

   ```text
   SUPABASE_DB_URL host: aws-1-ap-northeast-2.pooler.supabase.com:6543
   ```

   Artinya restart/recreate Docker sekarang akan mengganti env container dengan nilai host saat ini. Jangan restart sebelum `.env` dibereskan.

4. Direct DB host `db.myehfjbgpykyekfrjczl.supabase.co:5432` gagal TCP dari host lokal.

   Gunakan connection string **Transaction pooler** Supabase (`*.pooler.supabase.com:6543`) untuk local/Docker development.

5. LangGraph checkpointer masih fallback ke `InMemorySaver`.

   Root cause dari container:

   ```text
   ImportError: no pq wrapper available
   psycopg_binary missing, psycopg_c missing, libpq library not found
   ```

   Jadi `SUPABASE_DB_URL` saja tidak cukup. Image backend perlu salah satu:

   - dependency Python `psycopg[binary]`, atau
   - system package `libpq5` di Docker image.

## Yang perlu diambil dari Supabase dashboard

Ambil dan isi ulang `.env` sebagai satu paket:

| Env var | Lokasi |
| --- | --- |
| `SUPABASE_URL` | Settings -> API -> Project URL |
| `SUPABASE_ANON_KEY` | Settings -> API -> Project API keys -> anon/public atau publishable key |
| `NEXT_PUBLIC_SUPABASE_URL` | Sama dengan `SUPABASE_URL` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Sama dengan anon/publishable key |
| `SUPABASE_JWT_SECRET` | Settings -> API -> JWT Secret |
| `SUPABASE_SERVICE_ROLE_KEY` | Settings -> API -> service_role/secret key |
| `SUPABASE_DB_URL` | Settings -> Database -> Connection string -> Transaction pooler, port `6543` |

## Keputusan operasional

Jangan jalankan `docker compose restart` / recreate dulu sampai:

1. `SUPABASE_SERVICE_ROLE_KEY` terisi.
2. `SUPABASE_ANON_KEY` dan `NEXT_PUBLIC_SUPABASE_ANON_KEY` memakai key publik (`sb_publishable_*` atau anon JWT), bukan `sb_secret_*`.
3. `SUPABASE_DB_URL` di `.env` host memakai transaction pooler `*.pooler.supabase.com:6543`.
4. Backend image diperbaiki agar `PostgresSaver` bisa import `psycopg` dengan benar.

Setelah empat poin itu selesai, rebuild/restart backend:

```bash
docker compose up --build -d backend
```

Lalu verifikasi:

```bash
docker compose exec -T backend uv run python -c "from app.core.checkpointer import get_checkpointer; print(type(get_checkpointer()).__name__)"
```

Target hasil:

```text
PostgresSaver
```
