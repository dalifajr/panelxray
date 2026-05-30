@extends('layouts.app')

@section('content')
<div class="container-fluid px-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0 text-dark fw-bold">Dompet Keuangan</h2>
    </div>

    <div class="row">
        <!-- Saldo Info -->
        <div class="col-md-4 mb-4">
            <div class="card bg-primary text-white border-0 shadow-sm lift-hover">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <div class="text-white mb-1">Total Saldo Aktif</div>
                            <h3 class="mb-0 fw-bold">Rp {{ number_format(Auth::user()->balance, 0, ',', '.') }}</h3>
                        </div>
                        <div class="fs-1 text-white">
                            <i class="fas fa-wallet"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Topup Form -->
        <div class="col-md-8 mb-4">
            <div class="card border-0 shadow-sm lift-hover h-100">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-plus-circle me-2 text-success"></i>Isi Saldo (Top Up)</h5>
                </div>
                <div class="card-body p-4">
                    @if($pendingTopup)
                        <div class="alert alert-warning border-0 d-flex gap-3 shadow-sm align-items-start">
                            <i class="fas fa-exclamation-triangle fs-3 text-dark mt-1"></i>
                            <div>
                                <h5 class="alert-heading fw-bold text-dark mb-1">Selesaikan Pembayaran Sebelumnya</h5>
                                <p class="mb-1 text-dark">Sisa waktu pembayaran: <span id="countdown" class="fw-bold text-danger">05:00</span></p>
                                <hr class="border-dark opacity-25">
                                <p class="mb-1 text-dark fw-bold">Total Tagihan: Rp {{ number_format($pendingTopup->total_amount, 0, ',', '.') }}</p>
                                <p class="small text-dark mb-3">Silakan scan QRIS di bawah ini dengan aplikasi pembayaran Anda.</p>
                                
                                <div class="text-center p-3 bg-white rounded mb-3">
                                    @if($dynamicQris)
                                        <img src="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={{ urlencode($dynamicQris) }}" alt="QRIS Dinamis" class="img-fluid rounded border shadow-sm">
                                        <div class="mt-2 text-muted small">Nominal sudah terisi otomatis</div>
                                    @else
                                        <div class="text-danger"><i class="fas fa-times-circle"></i> Admin belum mengatur QRIS.</div>
                                    @endif
                                </div>
                                
                                <form action="{{ route('wallet.cancel') }}" method="POST" class="d-inline" id="autoCancelTopupForm">
                                    @csrf
                                    <button type="submit" class="btn btn-sm btn-outline-danger w-100"><i class="fas fa-times-circle me-1"></i>Batalkan Top Up Ini</button>
                                </form>
                            </div>
                        </div>
                    @else
                        <form action="{{ route('wallet.topup') }}" method="POST">
                            @csrf
                            <div class="mb-3">
                                <label class="form-label fw-bold">Nominal Top Up</label>
                                <div class="input-group">
                                    <span class="input-group-text bg-light border">Rp</span>
                                    <input type="number" name="amount" class="form-control border" min="5000" step="5000" placeholder="Minimal Rp 5.000" required>
                                </div>
                                <div class="form-text">Masukkan nominal kelipatan 5000.</div>
                            </div>
                            <button type="submit" class="btn btn-success w-100">Buat Instruksi Pembayaran</button>
                        </form>
                    @endif
                </div>
            </div>
        </div>
    </div>

    <!-- Riwayat Transaksi -->
    <div class="card border-0 shadow-sm lift-hover mb-4">
        <div class="card-header bg-white border-0 pt-4 pb-0 d-flex justify-content-between align-items-center">
            <h5 class="mb-0 fw-bold"><i class="fas fa-history text-info me-2"></i>Riwayat Transaksi</h5>
        </div>
        <div class="card-body p-0 mt-3">
            <div class="table-responsive">
                <table class="table table-hover mb-0">
                    <thead class="table-light">
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
                            <td class="px-4 font-monospace small">{{ $trx->reference }}</td>
                            <td class="px-4">
                                @if($trx->type == 'topup')
                                <span class="badge bg-primary">Top Up</span>
                                @else
                                <span class="badge bg-danger">Beli VPN</span>
                                @endif
                            </td>
                            <td class="px-4">{{ $trx->description ?? '-' }}</td>
                            <td class="px-4 text-end fw-bold {{ in_array($trx->type, ['topup', 'refund']) ? 'text-success' : 'text-danger' }}">
                                {{ in_array($trx->type, ['topup', 'refund']) ? '+' : '-' }} Rp {{ number_format($trx->total_amount, 0, ',', '.') }}
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
        <div class="card-footer bg-white border-0 pb-4">
            {{ $transactions->links() }}
        </div>
        @endif
    </div>
</div>

@if($pendingTopup)
@push('scripts')
<script>
    document.addEventListener('DOMContentLoaded', function() {
        var targetTime = {{ $pendingTopup->created_at->copy()->addSeconds(300)->timestamp * 1000 }};

        var countdownElement = document.getElementById('countdown');

        var cancelTriggered = false;
        var interval = setInterval(function() {
            var now = new Date().getTime();
            var distance = targetTime - now;

            if (distance <= 0) {
                clearInterval(interval);
                if(countdownElement) countdownElement.innerHTML = "WAKTU HABIS";
                if (!cancelTriggered) {
                    cancelTriggered = true;
                    var cancelForm = document.getElementById('autoCancelTopupForm');
                    if (cancelForm) {
                        cancelForm.submit();
                    } else {
                        window.location.href = "{{ route('wallet.index') }}";
                    }
                }
                return;
            }

            var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            var seconds = Math.floor((distance % (1000 * 60)) / 1000);

            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;

            if(countdownElement) countdownElement.innerHTML = minutes + ":" + seconds;

            // Check status via AJAX every 3 seconds
            if (seconds % 3 === 0) {
                fetch(`{{ route('transaction.status', $pendingTopup->id) }}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success' || data.status === 'cancelled') {
                            clearInterval(interval);
                            window.location.reload();
                        }
                    })
                    .catch(error => console.error('Error fetching status:', error));
            }
        }, 1000);
    });
</script>
@endpush
@endif

@endsection
