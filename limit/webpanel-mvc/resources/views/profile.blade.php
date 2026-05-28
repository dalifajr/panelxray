@extends('layouts.app')

@section('content')
<div class="container py-4">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card shadow-sm border-0">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h4 class="fw-bold mb-0 text-uppercase"><i class="fas fa-user-circle text-primary me-2"></i> Profil Pengguna</h4>
                </div>
                <div class="card-body p-4">
                    <form action="{{ route('profile.update') }}" method="POST">
                        @csrf
                        <div class="mb-3">
                            <label class="form-label text-muted fw-bold small text-uppercase">ID Telegram</label>
                            <input type="text" class="form-control bg-light" value="{{ explode('@', $user->email)[0] }}" disabled>
                        </div>
                        <div class="mb-4">
                            <label class="form-label fw-bold">Nama Tampilan Web Panel</label>
                            <input type="text" name="name" class="form-control" value="{{ old('name', $user->name) }}" required>
                            <div class="form-text">Nama ini akan ditampilkan di menu Sidebar dan Dashboard Panel.</div>
                        </div>

                        <div class="d-grid gap-2">
                            <button type="submit" class="btn btn-primary btn-lg">Simpan Perubahan</button>
                            <a href="{{ route('dashboard') }}" class="btn btn-light">Kembali ke Dashboard</a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection
