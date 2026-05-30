@extends('layouts.app')

@section('content')
<div class="container-fluid px-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0 text-dark fw-bold">Kelola Kode Voucher</h2>
    </div>

    @if(session('sweet_success'))
        <div class="alert alert-success border-0 shadow-sm mb-4">
            <i class="fas fa-check-circle me-2"></i>{{ session('sweet_success') }}
        </div>
    @endif

    @if($errors->any())
        <div class="alert alert-danger border-0 shadow-sm mb-4">
            <ul class="mb-0">
                @foreach($errors->all() as $error)
                    <li><i class="fas fa-exclamation-triangle me-2"></i>{{ $error }}</li>
                @endforeach
            </ul>
        </div>
    @endif

    <div class="row">
        <!-- Tambah Voucher Baru -->
        <div class="col-md-4 mb-4">
            <div class="card border-0 shadow-sm lift-hover">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h5 class="mb-0 fw-bold text-dark"><i class="fas fa-plus-circle me-2 text-primary"></i>Buat Voucher Baru</h5>
                </div>
                <div class="card-body p-4">
                    <form action="{{ route('admin.vouchers.store') }}" method="POST">
                        @csrf
                        <div class="mb-3">
                            <label class="form-label fw-bold text-secondary">Kode Voucher</label>
                            <input type="text" class="form-control border text-uppercase" name="code" value="{{ old('code') }}" required placeholder="MISAL: DISKON50" style="text-transform: uppercase;">
                            <small class="text-muted">Hanya boleh huruf, angka, underscore (_), atau dash (-).</small>
                        </div>

                        <div class="mb-3">
                            <label class="form-label fw-bold text-secondary">Benefit Dropdown</label>
                            <select class="form-select border" name="type" required>
                                <option value="free_balance" {{ old('type') === 'free_balance' ? 'selected' : '' }}>Saldo Gratis</option>
                                <option value="double_saldo" {{ old('type') === 'double_saldo' ? 'selected' : '' }}>Double Saldo (Deposit Terlipat Ganda)</option>
                            </select>
                        </div>

                        <div class="mb-3">
                            <label class="form-label fw-bold text-secondary">Nilai Benefit (Rupiah / Multiplier)</label>
                            <div class="input-group">
                                <span class="input-group-text bg-light border">Rp / X</span>
                                <input type="number" class="form-control border" name="benefit_value" value="{{ old('benefit_value', '0') }}" min="0" required>
                            </div>
                            <small class="text-muted">Isi nominal saldo gratis untuk "Saldo Gratis". Untuk "Double Saldo", ini bisa berupa limit maksimal ekstra saldo (0 = tanpa limit ekstra).</small>
                        </div>

                        <div class="mb-3">
                            <label class="form-label fw-bold text-secondary">Batas Kuota Penggunaan</label>
                            <div class="input-group">
                                <span class="input-group-text bg-light border"><i class="fas fa-users"></i></span>
                                <input type="number" class="form-control border" name="usage_limit" value="{{ old('usage_limit', '1') }}" min="1" required>
                            </div>
                            <small class="text-muted">Maksimal berapa kali voucher dapat diklaim di sistem.</small>
                        </div>

                        <div class="mb-4">
                            <label class="form-label fw-bold text-secondary">Masa Berlaku (Expired)</label>
                            <input type="date" class="form-control border" name="expires_at" value="{{ old('expires_at') }}">
                            <small class="text-muted">Kosongkan jika voucher berlaku selamanya.</small>
                        </div>

                        <button type="submit" class="btn btn-primary w-100 py-2 fw-bold"><i class="fas fa-save me-2"></i>Simpan Voucher</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- Daftar Voucher -->
        <div class="col-md-8 mb-4">
            <div class="card border-0 shadow-sm">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h5 class="mb-0 fw-bold text-dark"><i class="fas fa-ticket-alt me-2 text-primary"></i>Daftar Kode Voucher Aktif</h5>
                </div>
                <div class="card-body p-4">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>Kode</th>
                                    <th>Benefit / Jenis</th>
                                    <th class="text-center">Nilai</th>
                                    <th class="text-center">Kuota (Terpakai / Batas)</th>
                                    <th class="text-center">Masa Berlaku</th>
                                    <th class="text-center">Aksi</th>
                                </tr>
                            </thead>
                            <tbody>
                                @forelse($vouchers as $voucher)
                                <tr>
                                    <td>
                                        <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-3 py-2 fs-6 font-monospace">{{ $voucher->code }}</span>
                                    </td>
                                    <td>
                                        @if($voucher->type === 'free_balance')
                                            <span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="fas fa-coins me-1"></i>Saldo Gratis</span>
                                        @else
                                            <span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle px-2 py-1"><i class="fas fa-copy me-1"></i>Double Saldo</span>
                                        @endif
                                    </td>
                                    <td class="text-center fw-bold text-dark">
                                        @if($voucher->type === 'free_balance')
                                            Rp {{ number_format($voucher->benefit_value, 0, ',', '.') }}
                                        @else
                                            {{ $voucher->benefit_value > 0 ? 'Maks Rp ' . number_format($voucher->benefit_value, 0, ',', '.') : 'Tanpa Limit' }}
                                        @endif
                                    </td>
                                    <td class="text-center">
                                        <div class="fw-bold">{{ $voucher->usages_count }} / {{ $voucher->usage_limit }}</div>
                                        <div class="progress mt-1" style="height: 5px;">
                                            @php
                                                $percentage = ($voucher->usage_limit > 0) ? ($voucher->usages_count / $voucher->usage_limit) * 100 : 0;
                                            @endphp
                                            <div class="progress-bar bg-primary" role="progressbar" style="width: {{ $percentage }}%"></div>
                                        </div>
                                    </td>
                                    <td class="text-center text-secondary small">
                                        @if($voucher->expires_at)
                                            @if($voucher->expires_at->isPast())
                                                <span class="text-danger fw-bold"><i class="fas fa-calendar-times me-1"></i>Expired ({{ $voucher->expires_at->format('d M Y') }})</span>
                                            @else
                                                <span class="text-success"><i class="fas fa-calendar-check me-1"></i>Sampai {{ $voucher->expires_at->format('d M Y') }}</span>
                                            @endif
                                        @else
                                            <span class="text-muted"><i class="fas fa-infinity me-1"></i>Selamanya</span>
                                        @endif
                                    </td>
                                    <td class="text-center">
                                        <form action="{{ route('admin.vouchers.destroy', $voucher->id) }}" method="POST" class="d-inline-block form-delete-voucher">
                                            @csrf
                                            @method('DELETE')
                                            <button type="submit" class="btn btn-sm btn-outline-danger btn-delete-voucher" title="Hapus Voucher">
                                                <i class="fas fa-trash-alt"></i>
                                            </button>
                                        </form>
                                    </td>
                                </tr>
                                @empty
                                <tr>
                                    <td colspan="6" class="text-center py-4 text-muted">
                                        <i class="fas fa-ticket-alt fa-2x mb-2 d-block opacity-50"></i>
                                        Belum ada kode voucher yang terdaftar.
                                    </td>
                                </tr>
                                @endforelse
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function () {
    const deleteForms = document.querySelectorAll('.form-delete-voucher');
    deleteForms.forEach(form => {
        const btn = form.querySelector('.btn-delete-voucher');
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            Swal.fire({
                title: 'Hapus Voucher?',
                text: 'Kode voucher ini akan dihapus permanen dari sistem dan tidak bisa digunakan kembali!',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#3085d6',
                confirmButtonText: 'Ya, Hapus!',
                cancelButtonText: 'Batal'
            }).then((result) => {
                if (result.isConfirmed) {
                    form.submit();
                }
            });
        });
    });
});
</script>
@endsection
