@extends('layouts.app')

@section('content')
<div class="container-fluid px-4">
    <div class="row justify-content-center">
        <div class="col-md-6 mb-4">
            <div class="card border-0 shadow-sm lift-hover h-100">
                <div class="card-header bg-white border-0 pt-4 pb-0 text-center">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-qrcode me-2 text-primary"></i>Pembayaran QRIS</h5>
                </div>
                <div class="card-body p-4 text-center">
                    <div class="alert alert-warning border-0 d-flex gap-3 shadow-sm align-items-start mb-4">
                        <i class="fas fa-exclamation-triangle fs-3 text-dark mt-1"></i>
                        <div class="text-start">
                            <h5 class="alert-heading fw-bold text-dark mb-1">Selesaikan Pembayaran Anda</h5>
                            <p class="mb-1 text-dark">Sisa waktu pembayaran: <span id="countdown" class="fw-bold text-danger">05:00</span></p>
                        </div>
                    </div>

                    <h6 class="text-secondary mb-1">Total Tagihan</h6>
                    <h2 class="fw-bold text-dark mb-4">Rp {{ number_format($transaction->total_amount, 0, ',', '.') }}</h2>

                    <div class="bg-light p-3 rounded mb-4 d-inline-block shadow-sm">
                        @if($dynamicQris)
                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={{ urlencode($dynamicQris) }}" alt="QRIS Dinamis" class="img-fluid rounded border">
                            <div class="mt-2 text-muted small">Scan dengan aplikasi pembayaran Anda</div>
                        @else
                            <div class="text-danger"><i class="fas fa-times-circle"></i> Admin belum mengatur QRIS.</div>
                        @endif
                    </div>

                    <div class="text-start bg-light p-3 rounded mb-4 text-dark text-sm">
                        <p class="mb-1"><strong>Layanan:</strong> VPN {{ strtoupper($transaction->metadata['protocol']) }}</p>
                        <p class="mb-1"><strong>Username:</strong> {{ $transaction->metadata['username'] }}</p>
                        <p class="mb-0"><strong>Masa Aktif:</strong> {{ $transaction->metadata['days'] }} Hari</p>
                    </div>

                    <form action="{{ route('checkout.cancel', $transaction->id) }}" method="POST">
                        @csrf
                        <button type="submit" class="btn btn-outline-danger w-100"><i class="fas fa-times-circle me-1"></i>Batalkan Pesanan</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>

@push('scripts')
<script>
    document.addEventListener('DOMContentLoaded', function() {
        @php
            $remainingSeconds = 300 - \Carbon\Carbon::now()->diffInSeconds($transaction->created_at);
            if ($remainingSeconds < 0) $remainingSeconds = 0;
        @endphp
        
        var remainingSeconds = {{ $remainingSeconds }};
        var targetTime = new Date().getTime() + (remainingSeconds * 1000);

        var countdownElement = document.getElementById('countdown');

        var interval = setInterval(function() {
            var now = new Date().getTime();
            var distance = targetTime - now;

            if (distance < 0) {
                clearInterval(interval);
                countdownElement.innerHTML = "WAKTU HABIS";
                // Redirect otomatis untuk membatalkan
                window.location.reload();
                return;
            }

            var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            var seconds = Math.floor((distance % (1000 * 60)) / 1000);

            // Pad with 0
            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;

            countdownElement.innerHTML = minutes + ":" + seconds;
        }, 1000);
    });
</script>
@endpush
@endsection
