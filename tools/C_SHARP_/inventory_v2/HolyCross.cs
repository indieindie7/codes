using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;

namespace Assets.Scripts.PlayerInventorySystem.ItemsFolder
{
    class HolyCross : ItemLevel
    {
        public override void Start()
        {
            base.Start();
            myAction= delegate(Transform t){ print("foice"); };
        }
    }
}
