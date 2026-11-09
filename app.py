from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename

from datetime import datetime
import os


app = Flask(__name__)


# =========================================
# KONFIGURASI
# =========================================

app.secret_key = "ptpn-pks-pulo-tiga-cuti"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "db_cuti_ptpn"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

# Folder upload
app.config["UPLOAD_FOLDER"] = "static/uploads"

os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)

mysql = MySQL(app)


# =========================================
# HALAMAN INDEX
# =========================================

@app.route("/")
def index():
    return render_template("index.html")


# =========================================
# LOGIN
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if not username or not password or not role:
            flash(
                "Username, password, dan role wajib diisi.",
                "danger"
            )

            return render_template("login.html")

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT *
            FROM users
            WHERE username = %s
            AND password = %s
            AND role = %s
        """, (
            username,
            password,
            role
        ))

        user = cur.fetchone()

        cur.close()

        if user:

            session["loggedin"] = True
            session["id_user"] = user["id_user"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            if role == "admin":
                return redirect(
                    url_for("dashboard_admin")
                )

            return redirect(
                url_for("dashboard_karyawan")
            )

        flash(
            "Username, password, atau role salah!",
            "danger"
        )

    return render_template("login.html")


# =========================================
# LOGOUT
# =========================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Anda berhasil logout.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# =========================================
# DASHBOARD ADMIN
# =========================================

@app.route("/admin/dashboard")
def dashboard_admin():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    # Jumlah karyawan aktif
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM karyawan
        WHERE status = 'Aktif'
    """)

    total_karyawan = cur.fetchone()["total"]

    # Pengajuan menunggu
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM pengajuan_cuti
        WHERE status = 'Menunggu'
    """)

    pengajuan_menunggu = cur.fetchone()["total"]

    # Pengajuan disetujui
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM pengajuan_cuti
        WHERE status = 'Disetujui'
    """)

    pengajuan_disetujui = cur.fetchone()["total"]

    # Pengajuan ditolak
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM pengajuan_cuti
        WHERE status = 'Ditolak'
    """)

    pengajuan_ditolak = cur.fetchone()["total"]

    # Pengajuan terbaru
    cur.execute("""
        SELECT
            pengajuan_cuti.*,
            karyawan.nama,
            jenis_cuti.nama_jenis
        FROM pengajuan_cuti
        JOIN karyawan
            ON pengajuan_cuti.id_karyawan =
               karyawan.id_karyawan
        JOIN jenis_cuti
            ON pengajuan_cuti.id_jenis =
               jenis_cuti.id_jenis
        ORDER BY pengajuan_cuti.tanggal_pengajuan DESC
        LIMIT 5
    """)

    pengajuan_terbaru = cur.fetchall()

    cur.close()

    return render_template(
        "admin/dashboard.html",
        total_karyawan=total_karyawan,
        pengajuan_menunggu=pengajuan_menunggu,
        pengajuan_disetujui=pengajuan_disetujui,
        pengajuan_ditolak=pengajuan_ditolak,
        pengajuan_terbaru=pengajuan_terbaru
    )


# =========================================
# DATA KARYAWAN
# =========================================

@app.route("/admin/karyawan")
def data_karyawan():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT *
        FROM karyawan
        ORDER BY id_karyawan DESC
    """)

    karyawan = cur.fetchall()

    cur.close()

    return render_template(
        "admin/data_karyawan.html",
        karyawan=karyawan
    )


# =========================================
# TAMBAH KARYAWAN
# =========================================

@app.route(
    "/admin/karyawan/tambah",
    methods=["GET", "POST"]
)
def tambah_karyawan():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":

        nik = request.form.get("nik", "").strip()
        nama = request.form.get("nama", "").strip()
        jabatan = request.form.get("jabatan", "").strip()
        bagian = request.form.get("bagian", "").strip()
        no_hp = request.form.get("no_hp", "").strip()
        alamat = request.form.get("alamat", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not all([
            nik,
            nama,
            jabatan,
            bagian,
            username,
            password
        ]):
            flash(
                "Data wajib diisi dengan lengkap.",
                "danger"
            )

            return redirect(
                url_for("tambah_karyawan")
            )

        cur = mysql.connection.cursor()

        try:

            # Cek username
            cur.execute("""
                SELECT id_user
                FROM users
                WHERE username = %s
            """, (username,))

            if cur.fetchone():
                flash(
                    "Username sudah digunakan.",
                    "danger"
                )

                cur.close()

                return redirect(
                    url_for("tambah_karyawan")
                )

            # Cek NIK
            cur.execute("""
                SELECT id_karyawan
                FROM karyawan
                WHERE nik = %s
            """, (nik,))

            if cur.fetchone():
                flash(
                    "NIK sudah terdaftar.",
                    "danger"
                )

                cur.close()

                return redirect(
                    url_for("tambah_karyawan")
                )

            # Buat akun user
            cur.execute("""
                INSERT INTO users
                (
                    username,
                    password,
                    role
                )
                VALUES
                (
                    %s,
                    %s,
                    'karyawan'
                )
            """, (
                username,
                password
            ))

            id_user = cur.lastrowid

            # Buat data karyawan
            cur.execute("""
                INSERT INTO karyawan
                (
                    nik,
                    nama,
                    jabatan,
                    bagian,
                    no_hp,
                    alamat,
                    status,
                    id_user
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'Aktif',
                    %s
                )
            """, (
                nik,
                nama,
                jabatan,
                bagian,
                no_hp,
                alamat,
                id_user
            ))

            mysql.connection.commit()

            flash(
                "Data karyawan berhasil ditambahkan.",
                "success"
            )

        except Exception as e:

            mysql.connection.rollback()

            flash(
                "Gagal menambahkan karyawan: " + str(e),
                "danger"
            )

        finally:
            cur.close()

        return redirect(
            url_for("data_karyawan")
        )

    return render_template(
        "admin/tambah_karyawan.html"
    )


# =========================================
# EDIT KARYAWAN
# =========================================

@app.route(
    "/admin/karyawan/edit/<int:id_karyawan>",
    methods=["GET", "POST"]
)
def edit_karyawan(id_karyawan):

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        nik = request.form.get("nik", "").strip()
        nama = request.form.get("nama", "").strip()
        jabatan = request.form.get("jabatan", "").strip()
        bagian = request.form.get("bagian", "").strip()
        no_hp = request.form.get("no_hp", "").strip()
        alamat = request.form.get("alamat", "").strip()
        status = request.form.get("status", "Aktif")

        if not all([
            nik,
            nama,
            jabatan,
            bagian
        ]):
            cur.close()

            flash(
                "Data wajib diisi dengan lengkap.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_karyawan",
                    id_karyawan=id_karyawan
                )
            )

        try:

            cur.execute("""
                UPDATE karyawan
                SET
                    nik = %s,
                    nama = %s,
                    jabatan = %s,
                    bagian = %s,
                    no_hp = %s,
                    alamat = %s,
                    status = %s
                WHERE id_karyawan = %s
            """, (
                nik,
                nama,
                jabatan,
                bagian,
                no_hp,
                alamat,
                status,
                id_karyawan
            ))

            mysql.connection.commit()

            flash(
                "Data karyawan berhasil diperbarui.",
                "success"
            )

        except Exception as e:

            mysql.connection.rollback()

            flash(
                "Gagal memperbarui data: " + str(e),
                "danger"
            )

        finally:
            cur.close()

        return redirect(
            url_for("data_karyawan")
        )

    cur.execute("""
        SELECT *
        FROM karyawan
        WHERE id_karyawan = %s
    """, (id_karyawan,))

    karyawan = cur.fetchone()

    cur.close()

    if not karyawan:

        flash(
            "Data karyawan tidak ditemukan.",
            "danger"
        )

        return redirect(
            url_for("data_karyawan")
        )

    return render_template(
        "admin/edit_karyawan.html",
        karyawan=karyawan
    )


# =========================================
# HAPUS KARYAWAN
# =========================================

@app.route(
    "/admin/karyawan/hapus/<int:id_karyawan>"
)
def hapus_karyawan(id_karyawan):

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    try:

        cur.execute("""
            DELETE FROM karyawan
            WHERE id_karyawan = %s
        """, (id_karyawan,))

        mysql.connection.commit()

        flash(
            "Data karyawan berhasil dihapus.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        flash(
            "Gagal menghapus karyawan: " + str(e),
            "danger"
        )

    finally:
        cur.close()

    return redirect(
        url_for("data_karyawan")
    )


# =========================================
# DATA PENGAJUAN
# =========================================

@app.route("/admin/pengajuan")
def data_pengajuan():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            pengajuan_cuti.*,
            karyawan.nik,
            karyawan.nama,
            karyawan.jabatan,
            karyawan.bagian,
            jenis_cuti.nama_jenis
        FROM pengajuan_cuti
        JOIN karyawan
            ON pengajuan_cuti.id_karyawan =
               karyawan.id_karyawan
        JOIN jenis_cuti
            ON pengajuan_cuti.id_jenis =
               jenis_cuti.id_jenis
        ORDER BY
            pengajuan_cuti.tanggal_pengajuan DESC
    """)

    pengajuan = cur.fetchall()

    cur.close()

    return render_template(
        "admin/data_pengajuan.html",
        pengajuan=pengajuan
    )


# =========================================
# DETAIL PENGAJUAN
# =========================================

@app.route(
    "/admin/pengajuan/detail/<int:id_pengajuan>"
)
def detail_pengajuan(id_pengajuan):

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            pengajuan_cuti.*,
            karyawan.nik,
            karyawan.nama,
            karyawan.jabatan,
            karyawan.bagian,
            karyawan.no_hp,
            jenis_cuti.nama_jenis
        FROM pengajuan_cuti
        JOIN karyawan
            ON pengajuan_cuti.id_karyawan =
               karyawan.id_karyawan
        JOIN jenis_cuti
            ON pengajuan_cuti.id_jenis =
               jenis_cuti.id_jenis
        WHERE pengajuan_cuti.id_pengajuan = %s
    """, (id_pengajuan,))

    pengajuan = cur.fetchone()

    cur.close()

    if not pengajuan:

        flash(
            "Pengajuan tidak ditemukan.",
            "danger"
        )

        return redirect(
            url_for("data_pengajuan")
        )

    return render_template(
        "admin/detail_pengajuan.html",
        pengajuan=pengajuan
    )


# =========================================
# PROSES PENGAJUAN
# =========================================

@app.route(
    "/admin/pengajuan/proses/<int:id_pengajuan>",
    methods=["POST"]
)
def proses_pengajuan(id_pengajuan):

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    status = request.form.get("status")
    keterangan = request.form.get(
        "keterangan_admin",
        ""
    ).strip()

    if status not in [
        "Menunggu",
        "Disetujui",
        "Ditolak"
    ]:
        flash(
            "Status pengajuan tidak valid.",
            "danger"
        )

        return redirect(
            url_for(
                "detail_pengajuan",
                id_pengajuan=id_pengajuan
            )
        )

    cur = mysql.connection.cursor()

    try:

        cur.execute("""
            UPDATE pengajuan_cuti
            SET
                status = %s,
                keterangan_admin = %s
            WHERE id_pengajuan = %s
        """, (
            status,
            keterangan,
            id_pengajuan
        ))

        mysql.connection.commit()

        flash(
            "Pengajuan berhasil diproses.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        flash(
            "Gagal memproses pengajuan: " + str(e),
            "danger"
        )

    finally:
        cur.close()

    return redirect(
        url_for("data_pengajuan")
    )


# =========================================
# LAPORAN ADMIN
# =========================================

@app.route("/admin/laporan")
def laporan_admin():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    # Total
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM pengajuan_cuti
    """)

    total = cur.fetchone()["total"]

    # Menunggu
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM pengajuan_cuti
        WHERE status = 'Menunggu'
    """)

    menunggu = cur.fetchone()["total"]

    # Disetujui
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM pengajuan_cuti
        WHERE status = 'Disetujui'
    """)

    disetujui = cur.fetchone()["total"]

    # Ditolak
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM pengajuan_cuti
        WHERE status = 'Ditolak'
    """)

    ditolak = cur.fetchone()["total"]

    # Data laporan
    cur.execute("""
        SELECT
            pengajuan_cuti.*,
            karyawan.nik,
            karyawan.nama,
            karyawan.bagian,
            jenis_cuti.nama_jenis
        FROM pengajuan_cuti
        JOIN karyawan
            ON pengajuan_cuti.id_karyawan =
               karyawan.id_karyawan
        JOIN jenis_cuti
            ON pengajuan_cuti.id_jenis =
               jenis_cuti.id_jenis
        ORDER BY
            pengajuan_cuti.tanggal_pengajuan DESC
    """)

    laporan = cur.fetchall()

    cur.close()

    return render_template(
        "admin/laporan.html",
        total=total,
        menunggu=menunggu,
        disetujui=disetujui,
        ditolak=ditolak,
        laporan=laporan
    )


# =========================================
# DASHBOARD KARYAWAN
# =========================================

@app.route("/karyawan/dashboard")
def dashboard_karyawan():

    if session.get("role") != "karyawan":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT *
        FROM karyawan
        WHERE id_user = %s
    """, (session["id_user"],))

    karyawan = cur.fetchone()

    total_pengajuan = 0
    menunggu = 0
    disetujui = 0
    ditolak = 0

    if karyawan:

        cur.execute("""
            SELECT COUNT(*) AS total
            FROM pengajuan_cuti
            WHERE id_karyawan = %s
        """, (
            karyawan["id_karyawan"],
        ))

        total_pengajuan = cur.fetchone()["total"]

        cur.execute("""
            SELECT COUNT(*) AS total
            FROM pengajuan_cuti
            WHERE id_karyawan = %s
            AND status = 'Menunggu'
        """, (
            karyawan["id_karyawan"],
        ))

        menunggu = cur.fetchone()["total"]

        cur.execute("""
            SELECT COUNT(*) AS total
            FROM pengajuan_cuti
            WHERE id_karyawan = %s
            AND status = 'Disetujui'
        """, (
            karyawan["id_karyawan"],
        ))

        disetujui = cur.fetchone()["total"]

        cur.execute("""
            SELECT COUNT(*) AS total
            FROM pengajuan_cuti
            WHERE id_karyawan = %s
            AND status = 'Ditolak'
        """, (
            karyawan["id_karyawan"],
        ))

        ditolak = cur.fetchone()["total"]

    cur.close()

    return render_template(
        "karyawan/dashboard.html",
        karyawan=karyawan,
        total_pengajuan=total_pengajuan,
        menunggu=menunggu,
        disetujui=disetujui,
        ditolak=ditolak
    )


# =========================================
# AJUKAN CUTI
# =========================================

@app.route(
    "/karyawan/ajukan_cuti",
    methods=["GET", "POST"]
)
def ajukan_cuti():

    if session.get("role") != "karyawan":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    # Ambil data karyawan
    cur.execute("""
        SELECT *
        FROM karyawan
        WHERE id_user = %s
    """, (session["id_user"],))

    karyawan = cur.fetchone()

    # Ambil jenis cuti
    cur.execute("""
        SELECT *
        FROM jenis_cuti
        ORDER BY nama_jenis
    """)

    jenis_cuti = cur.fetchall()

    if not karyawan:

        cur.close()

        flash(
            "Data karyawan tidak ditemukan.",
            "danger"
        )

        return redirect(
            url_for("dashboard_karyawan")
        )

    if request.method == "POST":

        id_jenis = request.form.get("id_jenis")
        tanggal_mulai = request.form.get(
            "tanggal_mulai"
        )
        tanggal_selesai = request.form.get(
            "tanggal_selesai"
        )
        alasan = request.form.get(
            "alasan",
            ""
        ).strip()

        # Validasi
        if not all([
            id_jenis,
            tanggal_mulai,
            tanggal_selesai,
            alasan
        ]):

            cur.close()

            flash(
                "Semua data pengajuan wajib diisi.",
                "danger"
            )

            return redirect(
                url_for("ajukan_cuti")
            )

        try:

            mulai = datetime.strptime(
                tanggal_mulai,
                "%Y-%m-%d"
            )

            selesai = datetime.strptime(
                tanggal_selesai,
                "%Y-%m-%d"
            )

        except ValueError:

            cur.close()

            flash(
                "Format tanggal tidak valid.",
                "danger"
            )

            return redirect(
                url_for("ajukan_cuti")
            )

        # Cek tanggal
        if selesai < mulai:

            cur.close()

            flash(
                "Tanggal selesai tidak boleh sebelum tanggal mulai.",
                "danger"
            )

            return redirect(
                url_for("ajukan_cuti")
            )

        jumlah_hari = (
            selesai - mulai
        ).days + 1

        # File pendukung
        file = request.files.get(
            "file_pendukung"
        )

        nama_file = None

        if file and file.filename:

            nama_file = secure_filename(
                file.filename
            )

            if not nama_file:

                cur.close()

                flash(
                    "Nama file tidak valid.",
                    "danger"
                )

                return redirect(
                    url_for("ajukan_cuti")
                )

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    nama_file
                )
            )

        try:

            cur.execute("""
                INSERT INTO pengajuan_cuti
                (
                    id_karyawan,
                    id_jenis,
                    tanggal_mulai,
                    tanggal_selesai,
                    jumlah_hari,
                    alasan,
                    file_pendukung
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                karyawan["id_karyawan"],
                id_jenis,
                tanggal_mulai,
                tanggal_selesai,
                jumlah_hari,
                alasan,
                nama_file
            ))

            mysql.connection.commit()

            flash(
                "Pengajuan berhasil dikirim.",
                "success"
            )

        except Exception as e:

            mysql.connection.rollback()

            flash(
                "Gagal mengirim pengajuan: " + str(e),
                "danger"
            )

        finally:
            cur.close()

        return redirect(
            url_for("riwayat_karyawan")
        )

    cur.close()

    return render_template(
        "karyawan/ajukan_cuti.html",
        karyawan=karyawan,
        jenis_cuti=jenis_cuti
    )


# =========================================
# RIWAYAT KARYAWAN
# =========================================

@app.route("/karyawan/riwayat")
def riwayat_karyawan():

    if session.get("role") != "karyawan":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id_karyawan
        FROM karyawan
        WHERE id_user = %s
    """, (
        session["id_user"],
    ))

    karyawan = cur.fetchone()

    pengajuan = []

    if karyawan:

        cur.execute("""
            SELECT
                pengajuan_cuti.*,
                jenis_cuti.nama_jenis
            FROM pengajuan_cuti
            JOIN jenis_cuti
                ON pengajuan_cuti.id_jenis =
                   jenis_cuti.id_jenis
            WHERE pengajuan_cuti.id_karyawan = %s
            ORDER BY
                pengajuan_cuti.tanggal_pengajuan DESC
        """, (
            karyawan["id_karyawan"],
        ))

        pengajuan = cur.fetchall()

    cur.close()

    return render_template(
        "karyawan/riwayat.html",
        pengajuan=pengajuan
    )


# =========================================
# PROFIL KARYAWAN
# =========================================

@app.route("/karyawan/profil")
def profil_karyawan():

    if session.get("role") != "karyawan":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT *
        FROM karyawan
        WHERE id_user = %s
    """, (
        session["id_user"],
    ))

    karyawan = cur.fetchone()

    cur.close()

    return render_template(
        "karyawan/profil.html",
        karyawan=karyawan
    )


# =========================================
# JALANKAN APLIKASI
# =========================================

if __name__ == "__main__":
    app.run(debug=True)