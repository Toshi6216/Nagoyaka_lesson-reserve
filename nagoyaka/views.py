from django.shortcuts import render
from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = "nagoyaka/home.html"

class IndexView(TemplateView):
    template_name = "nagoyaka/index.html"

class AboutView(TemplateView):
    template_name = "nagoyaka/about.html"

class ProductsView(TemplateView):
    template_name = "nagoyaka/products.html"

class StoreView(TemplateView):
    template_name = "nagoyaka/store.html"