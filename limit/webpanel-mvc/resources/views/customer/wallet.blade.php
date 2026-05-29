@extends('layouts.app')

@section('content')
<div class="container-fluid px-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0 text-white">Dompet Keuangan</h2>
    </div>

    <div class="row">
        <!-- Saldo Info -->
        <div class="col-md-4 mb-4">
            <div class="card bg-primary text-white border-0 shadow-sm lift-hover">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <div class="text-white-50 small mb-1">Total Saldo Aktif</div>
                            <h3 class="mb-0">Rp {{ number_format(Auth::user()->balance, 0, ',', '.') }}</h3>
                        </div>
                        <div class="fs-1 text-white-50 opacity-50">
                            <i class="fas fa-wallet"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Topup Form -->
        <div class="col-md-8 mb-4">
            <div class="card border-0 shadow-sm lift-hover h-100">
                <div class="card-header bg-dark text-white border-bottom border-secondary">
                    <h5 class="mb-0"><i class="fas fa-plus-circle me-2 text-success"></i>Isi Saldo (Top Up)</h5>
                </div>
                <div class="card-body bg-dark text-white">
                    @if($pendingTopup)
                        <div class="alert alert-warning border-0 d-flex gap-3 shadow-sm align-items-start">
                            <i class="fas fa-exclamation-triangle fs-3 text-dark mt-1"></i>
                            <div>
                                <h5 class="alert-heading fw-bold text-dark mb-1">Selesaikan Pembayaran Sebelumnya</h5>
                                <p class="mb-1 text-dark">Anda memiliki transaksi topup yang belum dibayar.</p>
                                <hr class="border-dark opacity-25">
                                <p class="mb-1 text-dark fw-bold">Kode Unik / Total: Rp {{ number_format($pendingTopup->total_amount, 0, ',', '.') }}</p>
                                <p class="small text-dark mb-3">Silakan bayar menggunakan QRIS di bawah ini dengan nominal <b>TEPAT SESUAI TOTAL TRANSFER</b> hingga 3 digit terakhir.</p>
                                
                                <div class="text-center p-3 bg-white rounded">
                                    <h6 class="text-dark fw-bold mb-3">QRIS Pembayaran</h6>
                                    @if($qrisPayload)
                                        <img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={{ urlencode($qrisPayload) }}" alt="QRIS" class="img-fluid rounded border shadow-sm">
                                    @else
                                        <div class="text-danger"><i class="fas fa-times-circle"></i> Admin belum mengatur QRIS.</div>
                                    @endif
                                </div>
                            </div>
                        </div>
                    @else
                        <form action="{{ route('wallet.topup') }}" method="POST">
                            @csrf
                            <div class="mb-3">
                                <label class="form-label">Nominal Top Up</label>
                                <div class="input-group">
                                    <span class="input-group-text bg-secondary border-0 text-white">Rp</span>
                                    <input type="number" name="amount" class="form-control bg-dark text-white border-secondary" min="5000" step="5000" placeholder="Minimal Rp 5.000" required>
                                </div>
                                <div class="form-text text-secondary">Masukkan nominal kelipatan 5000.</div>
                            </div>
                            <button type="submit" class="btn btn-success w-100">Buat Instruksi Pembayaran</button>
                        </form>
                    @endif
                </div>
            </div>
        </div>
    </div>

    <!-- Riwayat Transaksi -->
    <div class="card border-0 shadow-sm lift-hover">
        <div class="card-header bg-dark text-white border-bottom border-secondary d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="fas fa-history text-info me-2"></i>Riwayat Transaksi</h5>
        </div>
        <div class="card-body bg-dark p-0">
            <div class="table-responsive">
                <table class="table table-dark table-hover mb-0">
                    <thead>
                        <tr>
                            <th class="px-4">Waktu</th>
                            <th class="px-4">Referensi</th>
                            <th class="px-4">Tipe</th>
                            <th class="px-4">Keterangan</th>
                            <th class="px-4 text-end">Nominal</th>
                            <th class="px-4 text-center">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($transactions as $trx)
                        <tr>
                            <td class="px-4 text-secondary small">{{ $trx->created_at->format('d M Y H:i') }}</td>
                            <td class="px-4 font-monospace small text-info">{{ $trx->reference }}</td>
                            <td class="px-4">
                                @if($trx->type == 'topup')
                                <span class="badge bg-primary">Top Up</span>
                                @else
                                <span class="badge bg-danger">Beli VPN</span>
                                @endif
                            </td>
                            <td class="px-4">{{ $trx->description ?? '-' }}</td>
                            <td class="px-4 text-end fw-bold {{ $trx->type == 'topup' ? 'text-success' : 'text-danger' }}">
                                {{ $trx->type == 'topup' ? '+' : '-' }} Rp {{ number_format($trx->total_amount, 0, ',', '.') }}
                            </td>
                            <td class="px-4 text-center">
                                @if($trx->status == 'success')
                                <span class="badge bg-success">Sukses</span>
                                @elseif($trx->status == 'pending')
                                <span class="badge bg-warning text-dark">Pending</span>
                                @else
                                <span class="badge bg-secondary">{{ ucfirst($trx->status) }}</span>
                                @endif
                            </td>
                        </tr>
                        @empty
                        <tr>
                            <td colspan="6" class="text-center text-muted py-4">Belum ada riwayat transaksi.</td>
                        </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </div>
        @if($transactions->hasPages())
        <div class="card-footer bg-dark border-secondary">
            {{ $transactions->links() }}
        </div>
        @endif
    </div>
</div>
@endsection
