﻿using System;
using System.Threading.Tasks;
using System.Windows.Input;
using RayshiftTranslateFGO.Services;
using Xamarin.Essentials;
using Xamarin.Forms;

namespace RayshiftTranslateFGO.ViewModels
{
    public class AboutViewModel : BaseViewModel
    {
        public AboutViewModel(ICacheProvider cache): base(cache)
        {
            Title = "About";
            OpenWebCommand = new Command(async () => await Browser.OpenAsync("https://rayshift.io/translate"));
            OpenGithub = new Command(async () => await Browser.OpenAsync("https://github.com/rayshift/translatefgo"));
        }

        public ICommand OpenWebCommand { get; }
        public ICommand OpenGithub { get; }
    }
}