using playerInventory;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
namespace playerBehaviour
{
    public class AttackController : MonoBehaviour
    {
        public SpecialSpot leftHand, rightHand;
        public Animator handAnimController;
        void Start()
        {
        }
        void Update()
        {
            if(Input.GetMouseButtonDown(0) && leftHand.Item != null)
            {
                leftHand.Item.origin.myAction(leftHand.objectTransform);
            }
            if (Input.GetMouseButtonDown(1) && rightHand.Item != null)
            {
                rightHand.Item.origin.myAction(rightHand.objectTransform);
            }
            handAnimController.SetBool("leftHand", leftHand.Item!=null);
            handAnimController.SetBool("rightHand", rightHand.Item!=null);
        }
    }
}
