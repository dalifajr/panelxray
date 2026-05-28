@extends('layouts.app')

@section('content')
<div class="container py-4">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card shadow-sm border-0">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h4 class="fw-bold mb-0 text-uppercase">Perpanjang Akun {{ strtoupper($protocol) }}</h4>
                </div>
                <div class="card-body p-4">
                    <p class="mb-4">Username: <strong>{{ $user }}</strong></p>

                    @if(session('error'))
                        <div class="alert alert-danger">{{ session('error') }}</div>
                    @endif
                    @if($errors->any())
                        <div class="alert alert-danger">
                            <ul class="mb-0">
                                @foreach($errors->all() as $error)
                                    <li>{{ $error }}</li>
                                @endforeach
                            </ul>
                        </div>
                    @endif

                    <form action="{{ route('vpn.renew.process', [$protocol, $user]) }}" method="POST">
                        @csrf
                        <div class="mb-4">
                            <label class="form-label fw-bold">Tambah Masa Aktif (Hari)</label>
                            <input type="number" name="days" class="form-control" value="30" min="1" max="365" required>
                        </div>

                        <div class="d-grid gap-2">
                            <button type="submit" class="btn btn-info text-white btn-lg">Perpanjang Sekarang</button>
                            <a href="{{ route('vpn.index', $protocol) }}" class="btn btn-light">Batal</a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection
