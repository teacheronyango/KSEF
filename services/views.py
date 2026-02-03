from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .forms import CustomUserCreationForm, ServiceRequestForm
from .models import ServiceRequest, ServiceCategory, UserProfile

def home(request):
    recent_requests = ServiceRequest.objects.filter(status='open')[:6]
    total_requests = ServiceRequest.objects.count()
    completed_requests = ServiceRequest.objects.filter(status='completed').count()
    active_volunteers = UserProfile.objects.filter(user_type='volunteer').count()

    context = {
        'recent_requests': recent_requests,
        'total_requests': total_requests,
        'completed_requests': completed_requests,
        'active_volunteers': active_volunteers,
    }
    return render(request, 'services/index.html', context)

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to KSEF.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'services/register.html', {'form': form})

@login_required
def dashboard(request):
    user_profile = UserProfile.objects.get(user=request.user)

    if user_profile.user_type == 'volunteer':
        my_assignments = ServiceRequest.objects.filter(volunteer=request.user)
        available_requests = ServiceRequest.objects.filter(status='open')[:10]
        context = {
            'user_profile': user_profile,
            'my_assignments': my_assignments,
            'available_requests': available_requests,
        }
    else:
        my_requests = ServiceRequest.objects.filter(requester=request.user)
        context = {
            'user_profile': user_profile,
            'my_requests': my_requests,
        }

    return render(request, 'services/dashboard.html', context)

@login_required
def post_request(request):
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.requester = request.user
            service_request.save()
            messages.success(request, 'Your service request has been posted successfully!')
            return redirect('request_list')
    else:
        form = ServiceRequestForm()
    return render(request, 'services/post_request.html', {'form': form})

def request_list(request):
    requests = ServiceRequest.objects.all()
    category_filter = request.GET.get('category')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')

    if category_filter:
        requests = requests.filter(category_id=category_filter)
    if status_filter:
        requests = requests.filter(status=status_filter)
    if search_query:
        requests = requests.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    categories = ServiceCategory.objects.all()
    context = {
        'requests': requests,
        'categories': categories,
        'selected_category': category_filter,
        'selected_status': status_filter,
        'search_query': search_query,
    }
    return render(request, 'services/request_list.html', context)

@login_required
def request_detail(request, pk):
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    user_profile = UserProfile.objects.get(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'volunteer' and user_profile.user_type == 'volunteer':
            if service_request.status == 'open':
                service_request.volunteer = request.user
                service_request.status = 'assigned'
                service_request.save()
                messages.success(request, 'You have successfully volunteered for this request!')
            else:
                messages.error(request, 'This request is no longer available.')

        elif action == 'complete' and service_request.volunteer == request.user:
            service_request.status = 'completed'
            service_request.completed_at = timezone.now()
            service_request.save()
            messages.success(request, 'Request marked as completed!')

        elif action == 'cancel' and service_request.requester == request.user:
            service_request.status = 'cancelled'
            service_request.save()
            messages.success(request, 'Request has been cancelled.')

        return redirect('request_detail', pk=pk)

    context = {
        'request': service_request,
        'user_profile': user_profile,
    }
    return render(request, 'services/request_detail.html', context)
